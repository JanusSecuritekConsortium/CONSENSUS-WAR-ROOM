"""Turn existing source readers into conversations for the attention scan.

Email reuses the read-only IMAP/Graph readers in integrations.msty.personal.connectors
and their DPAPI-protected credentials. Telegram and WhatsApp personal chats come from
telegram_user and whatsapp, each only once the user has signed in or linked it.
Nothing here writes to a mailbox or sends a message.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from email.utils import getaddresses
import re

from .store import digest, parse

MAIL_KINDS = ('imap', 'gmail', 'icloud', 'bridge', 'outlook')
AUTOMATED = re.compile(r'(no-?reply|do-?not-?reply|notifications?|mailer-daemon|bounce|newsletter|alerts?)@', re.I)
# Reply headers are often wrapped onto a second line by the mail client.
QUOTE_START = re.compile(r'^((?:On|El|Le|Am|Dne)\b[^\n]{4,200}\n?[^\n]{0,120}?'
                         r'(?:wrote|escribi[oó]|va escriure|a écrit|schrieb|napsal\(a\)|napsala?):'
                         r'|-----Original Message-----|_{10,}|From: .+)', re.M)
QUOTE_INLINE = re.compile(r'\s(?:On|El|Le|Am|Dne)\s[^\n]{4,200}?'
                          r'(?:wrote|escribi[oó]|va escriure|a écrit|schrieb|napsal\(a\)|napsala?):')
MAX_MESSAGE_CHARS = 1200


class SourceUnavailable(RuntimeError):
    pass


def strip_quoted(text: str) -> str:
    """Keep the new part of a reply; quoted history would only cost model time."""
    match = QUOTE_START.search(text)
    if match:
        text = text[:match.start()]
    lines = [line for line in text.splitlines() if not line.lstrip().startswith('>')]
    text = '\n'.join(lines).split('\n-- \n')[0]
    return ' '.join(text.split())[:MAX_MESSAGE_CHARS]


def strip_quoted_lines(text: str) -> str:
    """Like strip_quoted, but keeps line breaks; used for drafts, whose layout is part of the style."""
    for pattern in (QUOTE_START, QUOTE_INLINE):
        match = pattern.search(text)
        if match:
            text = text[:match.start()]
    lines = [line.rstrip() for line in text.strip().splitlines() if not line.lstrip().startswith('>')]
    return '\n'.join(lines).strip()


def first_address(value: str) -> tuple[str, str]:
    for name, address in getaddresses([value or '']):
        if '@' in address:
            return name.strip().strip('"'), address.strip().casefold()
    return '', ''


def thread_root(message: dict) -> str:
    references = re.findall(r'<[^>]+>', message.get('references') or '')
    return references[0] if references else (message.get('message_id') or message['id'])


def mail_threads(account_id: str, messages: list[dict], now: datetime, lookback_days: int) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    seen = set()
    for message in messages:
        identity = message.get('message_id') or message['id']
        if identity in seen:  # the same message can appear in Inbox and Sent
            continue
        seen.add(identity)
        groups.setdefault(thread_root(message), []).append(message)
    threads = []
    for root, group in groups.items():
        group.sort(key=lambda m: parse(m['date']))  # by instant: senders use different UTC offsets
        last = parse(group[-1]['date'])
        if last < now - timedelta(days=lookback_days):
            continue
        inbound = [m for m in group if m.get('direction') == 'inbox']
        sent = [m for m in group if m.get('direction') == 'sent']
        if inbound:
            name, address = first_address(inbound[-1].get('from', ''))
        else:
            name, address = first_address(sent[-1].get('to', ''))
        if not address:
            continue
        automated = not sent and all(m.get('bulk') or AUTOMATED.search(first_address(m.get('from', ''))[1] + '@')
                                     for m in inbound)
        threads.append({
            'key': 'email:' + digest(account_id, root, length=16),
            'channel': 'email', 'account': account_id, 'subject': (group[-1].get('subject') or '')[:200],
            'counterpart_address': address, 'counterpart_name': name,
            'automated': automated,
            'messages': [{'id': m.get('message_id') or m['id'], 'direction': 'sent' if m.get('direction') == 'sent' else 'inbound',
                          'at': m['date'], 'text': strip_quoted(m.get('body') or '') or '(no text)'} for m in group],
            'source_ref': f'{account_id}:{(group[-1].get("message_id") or group[-1]["id"])}',
        })
    return finish(threads)


def finish(threads: list[dict], editable: bool = False) -> list[dict]:
    """Set the latest direction and the fingerprint that decides whether a conversation is classified again.

    An email never changes under its Message-ID, so its ids are enough. Chat messages can be edited
    under the same id, so for chats the fingerprint also covers what each message says.
    """
    for thread in threads:
        thread['last_direction'] = thread['messages'][-1]['direction']
        thread['last_at'] = thread['messages'][-1]['at']
        parts = [m['id'] for m in thread['messages']] if not editable else [
            '\x1f'.join((m['id'], m['direction'], m['at'], m['text'])) for m in thread['messages']]
        thread['fingerprint'] = digest(*parts, length=24)
    return threads


def chat_threads(channel: str, chats: list[dict], now: datetime, lookback_days: int) -> list[dict]:
    """One conversation per personal chat, holding its messages from the lookback window.

    Each chat is {'chat', 'address', 'name', 'messages': [{'id', 'from_me', 'at', 'text'}]},
    with 'at' an aware ISO timestamp; 'automated' is optional.
    """
    since = now - timedelta(days=lookback_days)
    threads = []
    for chat in chats:
        messages = sorted((m for m in chat['messages'] if parse(m['at']) >= since),
                          key=lambda m: parse(m['at']))  # stable: same-second messages keep their order
        if not messages or not chat.get('address'):
            continue
        threads.append({
            'key': f'{channel}:' + digest(channel, chat['chat'], length=16),
            'channel': channel, 'account': channel, 'subject': '',
            'counterpart_address': chat['address'], 'counterpart_name': chat.get('name') or '',
            'automated': bool(chat.get('automated')),
            'messages': [{'id': f'{chat["chat"]}:{m["id"]}', 'direction': 'sent' if m['from_me'] else 'inbound',
                          'at': m['at'], 'text': ' '.join((m.get('text') or '').split())[:MAX_MESSAGE_CHARS] or '(no text)'}
                         for m in messages],
            'source_ref': f'{channel}:{chat["chat"]}:{messages[-1]["id"]}',
        })
    return finish(threads, editable=True)


def chat_source(channel: str, settings: dict, fetch):
    """fetch(now, days, limit) returns (chats, status); a failure only marks this channel unavailable."""
    def read(now: datetime):
        try:
            chats, status = fetch(now, settings['lookback_days'], settings['messages_per_folder'])
        except Exception as error:  # never surface server responses, numbers or session data
            return [], {channel: {'status': 'unavailable', 'error_type': type(error).__name__}}
        threads = chat_threads(channel, chats, now, settings['lookback_days'])
        return threads, {channel: dict(status, threads=len(threads))}
    return read


def default_readers(settings: dict) -> dict:
    """Email always; each chat channel once it has been set up and is not switched off."""
    from . import telegram_user, whatsapp
    readers = {'email': email_source(settings)}
    if settings['telegram_chats'] and telegram_user.configured():
        readers['telegram'] = chat_source('telegram', settings, telegram_user.fetch)
    if settings['whatsapp_chats'] and whatsapp.configured():
        readers['whatsapp'] = chat_source('whatsapp', settings, whatsapp.fetch)
    return readers


def email_source(settings: dict):
    """Read every configured mail account; each account succeeds or fails on its own."""
    def read(now: datetime):
        from integrations.msty.personal import connectors, store as accounts
        configured = [a for a in accounts.load()['accounts'] if a.get('kind') in MAIL_KINDS and a.get('enabled')]
        if settings['mail_accounts']:
            configured = [a for a in configured if a['id'] in settings['mail_accounts']]
        statuses, threads = {}, []
        for account in configured:
            try:
                result = connectors.READERS[account['kind']](account, now, days=settings['lookback_days'],
                                                             limit=settings['messages_per_folder'])
                found = mail_threads(account['id'], result['messages'], now, settings['lookback_days'])
                threads += found
                statuses['email:' + account['id']] = {'status': 'ok', 'threads': len(found),
                                                      'warnings': result.get('warnings', [])[:5]}
            except Exception as error:  # never surface server responses or credentials
                statuses['email:' + account['id']] = {'status': 'unavailable', 'error_type': type(error).__name__}
        return threads, statuses
    return read


def calendar_lookup(settings: dict):
    """Return a function that reports whether a proposed slot is free in the configured calendar."""
    cache: dict[str, list] = {}

    def events_on(day, now):
        from integrations.msty.personal import connectors, store as accounts
        key = day.isoformat()
        if key not in cache:
            calendars = [a for a in accounts.load()['accounts'] if a.get('kind') == 'calendar' and a.get('enabled')]
            if not calendars:
                raise SourceUnavailable('no calendar configured')
            start = datetime.combine(day, datetime.min.time(), settings['tz'])
            loaded = []
            for account in calendars:
                loaded += connectors.calendar_events(account, start, mode='morning')['events']
            cache[key] = loaded  # only a complete read is cached; a failed one must never look free
        return cache[key]

    def availability(event: dict, now: datetime) -> dict:
        if not event.get('date'):
            return {'status': 'unknown', 'detail': 'No date proposed yet'}
        day = datetime.strptime(event['date'], '%Y-%m-%d').date()
        try:
            events = events_on(day, now)
        except Exception as error:
            return {'status': 'unknown', 'detail': f'Calendar unavailable ({type(error).__name__})'}
        if event.get('time'):
            hour, minute = map(int, event['time'].split(':'))
            slot_start = datetime.combine(day, datetime.min.time(), settings['tz']).replace(hour=hour, minute=minute)
            slot_end = slot_start + timedelta(hours=2)
        else:
            slot_start = datetime.combine(day, datetime.min.time(), settings['tz'])
            slot_end = slot_start + timedelta(days=1)
        clashes = []
        for entry in events:
            if entry.get('transparent'):
                continue
            begins = datetime.fromisoformat(entry['start'])
            if entry.get('all_day'):
                if begins.date() == day:
                    clashes.append(entry)
                continue
            ends = datetime.fromisoformat(entry['end']) if entry.get('end') else begins + timedelta(hours=1)
            if begins < slot_end and ends > slot_start:
                clashes.append(entry)
        if clashes:
            first = clashes[0]
            when = datetime.fromisoformat(first['start']).strftime('%H:%M') if not first.get('all_day') else 'all day'
            return {'status': 'busy', 'detail': f'{first["title"][:60]} ({when})'}
        return {'status': 'free', 'detail': 'That time appears free' if event.get('time') else 'No events that day'}
    return availability
