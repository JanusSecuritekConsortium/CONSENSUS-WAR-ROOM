"""Periodic scan: read sources, classify only changed conversations, update state, export."""
from __future__ import annotations

from datetime import datetime
import json

from . import classify, config, export, google_contacts, log, notifier, priority, sources as source_readers, store
from .store import (APPOINTMENT_PROPOSED, CLOSED, COMMITMENT_OPEN, NEEDS_REPLY, NO_ACTION, SNOOZED,
                    WAITING_ON_ME, WAITING_ON_OTHER)


class ClaimLost(RuntimeError):
    """Another scan took the store over after this one stalled."""


def similar(a: str, b: str) -> bool:
    left, right = set(store.normalized(a).split()), set(store.normalized(b).split())
    return bool(left and right) and len(left & right) / len(left | right) >= 0.5


def open_items(db, thread_key: str, kind: str) -> list[dict]:
    rows = db.execute(f'SELECT * FROM items WHERE thread_key=? AND kind=? AND state NOT IN ({",".join("?" * len(CLOSED))})',
                      (thread_key, kind, *sorted(CLOSED)))
    return [store.row_dict(row) for row in rows]


def tier(confidence: float, settings: dict) -> str:
    if confidence >= settings['high_confidence']:
        return 'high'
    return 'medium' if confidence >= settings['medium_confidence'] else 'low'


def apply(db, thread: dict, result: dict, now: datetime, settings: dict, availability=None) -> list[str]:
    """Translate one validated classification into item changes. Returns touched item ids."""
    key, contact_id = thread['key'], thread['contact_id']
    name = db.execute('SELECT name FROM contacts WHERE id=?', (contact_id,)).fetchone()['name']
    messages = thread['messages']
    last = messages[-1]
    sent_positions = [i for i, m in enumerate(messages) if m['direction'] == 'sent']
    after_reply = messages[sent_positions[-1] + 1:] if sent_positions else messages
    level = tier(result['confidence'], settings)
    base = {'contact_id': contact_id, 'channel': thread['channel'], 'thread_key': key,
            'source_ref': thread.get('source_ref'), 'summary': result['summary'], 'action': result['action'],
            'confidence': result['confidence'], 'review': int(level == 'medium'), 'urgent': int(result['urgent'])}
    touched = []

    if last['direction'] == 'sent':
        for item in open_items(db, key, 'reply'):
            store.close_from_source(db, item['id'], 'replied', now)
            touched.append(item['id'])
        if result['waiting_on'] == 'contact' and level != 'low':
            wait_key = f'{key}:wait:{last["id"]}'
            for item in open_items(db, key, 'waiting'):
                if item['key'] != wait_key:
                    store.close_from_source(db, item['id'], 'superseded', now)
            touched.append(store.upsert_from_source(db, key=wait_key, kind='waiting', state=WAITING_ON_OTHER, now=now,
                fields=dict(base, title=f'Waiting for {name}', urgent=0, first_seen_at=last['at'])))
    else:
        for item in open_items(db, key, 'waiting'):
            store.close_from_source(db, item['id'], 'answered', now)
            touched.append(item['id'])
        if result['waiting_on'] == 'owner' and result['needs_reply'] and level != 'low':
            reply_key = f'{key}:reply:{last["id"]}'
            for item in open_items(db, key, 'reply'):
                if item['key'] != reply_key:
                    store.close_from_source(db, item['id'], 'superseded', now)
            subject = thread.get('subject') or thread['channel']
            touched.append(store.upsert_from_source(db, key=reply_key,
                kind='reply', state=NEEDS_REPLY if result['reply_kind'] == 'question' else WAITING_ON_ME, now=now,
                fields=dict(base, title=f'{name} — {subject}'[:160], follow_ups=len(after_reply),
                            first_seen_at=after_reply[0]['at'])))
        elif level == 'high':
            for item in open_items(db, key, 'reply'):
                store.close_from_source(db, item['id'], 'no_longer_needed', now)
                touched.append(item['id'])

    existing_commitments = open_items(db, key, 'commitment')
    promised_at = messages[sent_positions[-1]]['at'] if sent_positions else last['at']
    for commitment in result['commitments']:
        match = next((c for c in existing_commitments if similar(c['title'], commitment['text'])), None)
        if commitment['completed']:
            if match and commitment['confidence'] >= settings['high_confidence']:
                store.close_from_source(db, match['id'], 'detected_done', now)
                touched.append(match['id'])
            continue  # a promise already kept never becomes a reminder
        if commitment['confidence'] < settings['medium_confidence'] or not sent_positions:
            continue
        commit_key = match['key'] if match else f'{key}:commit:{store.normalized(commitment["text"])[:80]}'
        touched.append(store.upsert_from_source(db, key=commit_key, kind='commitment', state=COMMITMENT_OPEN, now=now,
            fields=dict(base, title=commitment['text'], summary=f'You promised {name}: {commitment["text"]}.'[:300],
                        action=commitment['text'], confidence=commitment['confidence'], urgent=0,
                        review=int(commitment['confidence'] < settings['high_confidence']),
                        due_at=commitment['due_date'], due_text=commitment['due_text'],
                        first_seen_at=match['first_seen_at'] if match else promised_at)))

    appointment = result['appointment']
    if appointment and appointment['confidence'] >= settings['medium_confidence']:
        current = open_items(db, key, 'appointment')
        if appointment['status'] == 'proposed':
            appt_key = current[0]['key'] if current else f'{key}:appt:{appointment["date"] or "undated"}'
            event = {'title': appointment['title'], 'date': appointment['date'], 'time': appointment['time'],
                     'status': 'proposed'}
            if availability:
                found = availability(event, now)
                event.update(availability=found['status'], availability_detail=found['detail'])
            touched.append(store.upsert_from_source(db, key=appt_key, kind='appointment', state=APPOINTMENT_PROPOSED,
                now=now, fields=dict(base, title=appointment['title'], event=event, confidence=appointment['confidence'],
                                     review=int(appointment['confidence'] < settings['high_confidence']),
                                     due_at=appointment['date'], first_seen_at=last['at'])))
        else:
            for item in current:
                store.close_from_source(db, item['id'], appointment['status'], now)
                touched.append(item['id'])

    remaining = db.execute(f'SELECT state FROM items WHERE thread_key=? AND state NOT IN ({",".join("?" * len(CLOSED))})',
                           (key, *sorted(CLOSED))).fetchall()
    order = [WAITING_ON_ME, NEEDS_REPLY, COMMITMENT_OPEN, APPOINTMENT_PROPOSED, WAITING_ON_OTHER, SNOOZED]
    states = {row['state'] for row in remaining}
    thread_state = next((state for state in order if state in states), NO_ACTION)
    db.execute('UPDATE threads SET state=?, processed_fingerprint=fingerprint, error=NULL, retained_json=?, updated_at=? '
               'WHERE key=?', (thread_state, json.dumps(result) if level == 'low' else None, store.iso(now), key))
    log.event('item_classified', thread=key, state=thread_state, tier=level, items=len([t for t in touched if t]))
    return [t for t in touched if t]


def refresh(db, now: datetime, settings: dict) -> None:
    """Expire snoozes and recompute time-based priority for everything still open."""
    store.wake_snoozed(db, now)
    settings = dict(settings, important_contacts=favourites(db, settings))
    activity = {row['key']: row['last_message_at'] for row in db.execute('SELECT key, last_message_at FROM threads')}
    rows = db.execute(f'SELECT * FROM items WHERE state NOT IN ({",".join("?" * len(CLOSED))})', sorted(CLOSED))
    for item in [store.row_dict(row) for row in rows]:
        item['last_activity'] = activity.get(item['thread_key'])
        level, overdue, reasons = priority.assess(item, now, settings)
        if (level, overdue, reasons) != (item['priority'], item['overdue'], item['priority_reasons']):
            db.execute('UPDATE items SET priority=?, overdue=?, priority_reasons=? WHERE id=?',
                       (level, int(overdue), json.dumps(reasons), item['id']))
            if priority.LEVEL[level] > priority.LEVEL[item['priority']]:
                log.event('item_escalated', item_id=item['id'], priority=level)


def favourites(db, settings: dict) -> list[str]:
    """Important contacts from settings plus the starred people in Google Contacts."""
    return sorted(set(settings['important_contacts']) | set(store.meta_get(db, 'favourite_contacts', [])))


def style_examples(threads: list[dict], address: str, limit: int, channel: str = 'email') -> list[str]:
    """The owner's own recent messages, to this person first, then on the same channel, so drafts sound like the owner.

    A chat reply copies how the owner writes chats, not email.
    """
    own = [(t['counterpart_address'] == address, t['channel'] == channel, store.parse(m['at']), m['text'])
           for t in threads for m in t['messages']
           if m['direction'] == 'sent' and m['text'] != '(no text)' and not m['text'].startswith('(')
           and len(m['text']) > (15 if t['channel'] == 'email' else 3)]
    own.sort(reverse=True)
    return list(dict.fromkeys(entry[-1] for entry in own))[:limit]


def draft_missing(db, threads: list[dict], settings: dict, now: datetime, drafter, hold=lambda: None) -> int:
    """Prepare a reply in the owner's style for open, confident, recent reply items. Never sent.

    hold() is called before each model request and before saving its draft; it raises ClaimLost
    once another scan owns the store.
    """
    by_key = {thread['key']: thread for thread in threads}
    rows = db.execute("SELECT * FROM items WHERE kind='reply' AND review=0 AND state IN (?,?) "
                      'AND id NOT IN (SELECT item_id FROM drafts)', (NEEDS_REPLY, WAITING_ON_ME)).fetchall()
    made = 0
    for item in [store.row_dict(row) for row in rows]:
        if priority.quiet(item):
            continue
        # A conversation that has left the inbox is drafted from its summary, still in the owner's style.
        thread = by_key.get(item['thread_key'])
        address = thread['counterpart_address'] if thread else next(iter(db.execute(
            'SELECT address FROM identities WHERE contact_id=?', (item['contact_id'],)).fetchone() or []), '')
        contact = db.execute('SELECT name FROM contacts WHERE id=?', (item['contact_id'],)).fetchone()
        hold()
        try:
            body = drafter(item, contact['name'] if contact else None, settings,
                           conversation=thread['messages'] if thread else None,
                           examples=style_examples(threads, address, settings['style_examples'], item['channel']))
        except classify.ModelUnavailable:
            break
        except classify.ModelOutputError:
            continue
        hold()
        db.execute('INSERT INTO drafts(item_id, body, model, created_at) VALUES(?,?,?,?)',
                   (item['id'], body, settings['model'], store.iso(now)))
        db.commit()
        log.event('draft_generated', item_id=item['id'], origin='scan')
        made += 1
    return made


def alert(db, settings: dict, now: datetime, notify) -> list[str]:
    """Interrupt only for very important items, once each; everything else waits for the daily brief."""
    sent = set(store.meta_get(db, 'alerted', []))
    important = favourites(db, settings)
    rows = db.execute(f'SELECT * FROM items WHERE state NOT IN ({",".join("?" * len(CLOSED))})', sorted(CLOSED))
    due = [item for item in map(store.row_dict, rows) if item['id'] not in sent and priority.alert_worthy(item, important)]
    if not due:
        return []
    names = {row['id']: row['name'] for row in db.execute('SELECT id, name FROM contacts')}
    text = '\n'.join(f'{names.get(i["contact_id"], "Someone")}: {i["summary"]}' for i in due[:3])
    if len(due) > 3:
        text += f'\n+ {len(due) - 3} more'
    try:
        notify('Needs you now', text)
    except Exception as error:  # an alert that cannot be shown is retried at the next scan
        log.event('alert_failed', error_type=type(error).__name__)
        return []
    store.meta_set(db, 'alerted', sorted(sent | {i['id'] for i in due}))
    log.event('alert_shown', items=[i['id'] for i in due])
    return [i['id'] for i in due]


def record_thread(db, thread: dict, now: datetime) -> None:
    name, address = thread.get('counterpart_name', ''), thread['counterpart_address']
    # Newsletters and no-reply senders never become contacts.
    thread['contact_id'] = None if thread['automated'] else store.contact_for(db, thread['channel'], address, name, now)
    db.execute('''INSERT INTO threads(key,channel,account,contact_id,address,subject,last_message_at,last_direction,
                                      fingerprint,updated_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET contact_id=excluded.contact_id,
                  address=excluded.address, subject=excluded.subject, last_message_at=excluded.last_message_at,
                  last_direction=excluded.last_direction, fingerprint=excluded.fingerprint, updated_at=excluded.updated_at''',
               (thread['key'], thread['channel'], thread['account'], thread['contact_id'], address.strip().casefold(),
                thread.get('subject', ''), thread['last_at'], thread['last_direction'], thread['fingerprint'],
                store.iso(now)))
    log.event('source_ingested', thread=thread['key'], messages=len(thread['messages']))


def local_classifier(settings: dict, now: datetime):
    warmed = []

    def call(thread):
        if not warmed:
            classify.warm(settings)
            warmed.append(True)
        return classify.classify(thread, settings, now)
    return call


def local_drafter(settings: dict):
    warmed = []

    def call(*args, **kwargs):
        if not warmed:
            classify.warm(settings)
            warmed.append(True)
        return classify.draft(*args, **kwargs)
    return call


def run(now: datetime | None = None, *, settings=None, readers=None, classifier=None, availability=None,
        drafter=None, notify=None) -> dict:
    settings = settings or config.load()
    now = now or store.utcnow()
    readers = readers if readers is not None else source_readers.default_readers(settings)
    classifier = classifier or local_classifier(settings, now)
    availability = availability if availability is not None else source_readers.calendar_lookup(settings)
    drafter = drafter or local_drafter(settings)
    notify = notify or notifier.desktop
    summary = {'started_at': store.iso(now), 'processed': 0, 'skipped_unchanged': 0, 'errors': 0, 'pending': 0,
               'drafts': 0, 'alerts': 0}
    with store.connect() as db:
        if store.meta_get(db, 'paused', False):
            return dict(summary, status='paused')
        owner = store.claim_scan(db, now)
        if not owner:
            return dict(summary, status='already_running')

        def hold():
            """Renew the claim before each slow step and each write after one; stop once another scan owns it."""
            if not store.renew_scan(db, owner, max(now, store.utcnow())):
                raise ClaimLost

        try:
            try:
                imported = google_contacts.sync(db, settings, now)
                if imported:
                    summary['contacts'] = imported
                    db.commit()
            except (OSError, ValueError) as error:
                log.event('source_error', source='google_contacts', error_type=type(error).__name__)
            statuses, threads = {}, []
            for name, read in readers.items():
                hold()
                try:
                    found, status = read(now)
                    threads += found
                    statuses.update(status)
                except Exception as error:
                    statuses[name] = {'status': 'unavailable', 'error_type': type(error).__name__}
                    log.event('source_error', source=name, error_type=type(error).__name__)
            for source, status in statuses.items():
                if status['status'] != 'ok':
                    log.event('source_error', source=source, error_type=status.get('error_type'))
            hold()
            for thread in threads:
                record_thread(db, thread, now)
            db.commit()
            processed = {row['key']: row['processed_fingerprint'] for row in db.execute('SELECT key, processed_fingerprint FROM threads')}
            changed = sorted((t for t in threads if processed.get(t['key']) != t['fingerprint']),
                             key=lambda t: store.parse(t['last_at']), reverse=True)
            summary['skipped_unchanged'] = len(threads) - len(changed)
            msty = 'not_needed'
            calls = 0
            for index, thread in enumerate(changed):
                if not thread['automated'] and calls >= settings['max_threads_per_scan']:
                    summary['pending'] = sum(not t['automated'] for t in changed[index:])
                    break
                hold()
                if thread['automated']:
                    db.execute("UPDATE threads SET state=?, processed_fingerprint=fingerprint, error=NULL WHERE key=?",
                               (NO_ACTION, thread['key']))
                    db.commit()
                    continue
                calls += 1
                try:
                    result = classifier(thread)
                    msty = 'ok'
                except classify.ModelUnavailable as error:
                    msty = 'unavailable'
                    summary['pending'] = sum(not t['automated'] for t in changed[index:])
                    log.event('model_error', kind='unavailable', error_type=str(error))
                    break
                except classify.ModelOutputError as error:
                    summary['errors'] += 1
                    db.execute('UPDATE threads SET error=? WHERE key=?', ('model_output: ' + str(error)[:80], thread['key']))
                    db.commit()
                    log.event('model_error', kind='invalid_output', thread=thread['key'], detail=str(error)[:80])
                    continue
                hold()
                apply(db, thread, result, now, settings, availability)
                db.commit()
                summary['processed'] += 1
            refresh(db, now, settings)
            db.commit()
            if settings['auto_drafts'] and msty != 'unavailable':
                summary['drafts'] = draft_missing(db, threads, settings, now, drafter, hold)
            hold()
            if settings['alert_now']:
                summary['alerts'] = len(alert(db, settings, now, notify))
            summary.update(status='ok', finished_at=store.iso(store.utcnow()), msty=msty, sources=statuses)
            store.meta_set(db, 'last_scan', summary)
            if msty in ('ok', 'unavailable'):
                store.meta_set(db, 'msty', {'status': msty, 'at': store.iso(now)})
        except ClaimLost:
            # Another scan took over after this one stalled; it carries on from what was saved.
            db.rollback()
            summary.update(status='claim_lost', finished_at=store.iso(store.utcnow()))
            log.event('scan_claim_lost')
        finally:
            db.commit()  # keep finished conversations even if a later step failed
            store.release_scan(db, owner)
            db.commit()
    if summary.get('status') == 'claim_lost':
        return summary  # the scan that took over writes the files
    export.write_all(settings, now)
    log.event('scan_finished', processed=summary['processed'], pending=summary['pending'], errors=summary['errors'])
    return summary
