from datetime import datetime, timedelta, timezone, date, time
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import html
import imaplib
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import ssl
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .store import secret_read, secret_write

TZ = ZoneInfo('Europe/Madrid')
MAX_BYTES = 2_000_000
SCOPES = ['Mail.Read', 'User.Read']


def plain(text):
    text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', text, flags=re.I | re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()


def next_week(now):
    local = now.astimezone(TZ)
    start = (local + timedelta(days=7-local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=7)


def imap_mail(account, now, days=30, limit=100):
    host = account['host']
    if account['kind'] == 'bridge' and host not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('Proton Bridge must use loopback')
    context = ssl.create_default_context(cafile=account.get('ca_file') or None)
    password = secret_read(account['id']).get('password')
    if not password:
        raise ValueError('Local credential not configured')
    if account.get('tls', 'ssl') == 'ssl':
        client = imaplib.IMAP4_SSL(host, int(account['port']), ssl_context=context, timeout=20)
    else:
        client = imaplib.IMAP4(host, int(account['port']), timeout=20)
        try:
            client.starttls(ssl_context=context)
        except Exception:
            client.shutdown()
            raise
    messages, warnings = [], []
    readable_folders = []
    with client:
        client.login(account['username'], password)
        folders = [('INBOX', 'inbox')]
        sent = account.get('sent_folder')
        if not sent:
            status, listing = client.list()
            for row in listing or []:
                if isinstance(row, bytes) and b'\\sent' in row.lower():
                    match = re.match(rb'\([^)]*\)\s+(?:"[^"]*"|NIL)\s+(.+)$', row)
                    if match:
                        sent = match[1].decode().strip('"')
                        break
        if sent:
            folders.append((sent, 'sent'))
        else:
            warnings.append('Sent folder unavailable: reply checks are incomplete')
        since = (now-timedelta(days=days)).strftime('%d-%b-%Y')
        for folder, direction in folders:
            status, _ = client.select('"' + folder.replace('\\', '\\\\').replace('"', '\\"') + '"', readonly=True)
            if status != 'OK':
                warnings.append(direction + ' folder unavailable')
                continue
            readable_folders.append(direction)
            validity = client.response('UIDVALIDITY')[1]
            validity = validity[0].decode() if validity and validity[0] else 'unknown'
            status, data = client.uid('search', None, 'SINCE', since)
            if status != 'OK':
                raise RuntimeError('IMAP search failed')
            ids = data[0].split() if data and data[0] else []
            if len(ids) > limit:
                warnings.append(direction + ' limited to latest ' + str(limit) + ' messages')
            for uid in ids[-limit:]:
                status, data = client.uid('fetch', uid, '(RFC822.SIZE)')
                metadata = b' '.join(x for x in data or [] if isinstance(x, bytes))
                size = re.search(rb'RFC822.SIZE\s+(\d+)', metadata)
                if status != 'OK' or not size or int(size[1]) > MAX_BYTES:
                    warnings.append('A message was skipped (size/metadata limit)')
                    continue
                status, data = client.uid('fetch', uid, '(BODY.PEEK[])')
                part = next((x for x in data or [] if isinstance(x, tuple)), None)
                if status != 'OK' or not part or len(part[1]) > MAX_BYTES:
                    warnings.append('A message could not be read')
                    continue
                message = BytesParser(policy=policy.default).parsebytes(part[1])
                try:
                    stamp = parsedate_to_datetime(str(message.get('Date', '')))
                    if not stamp.tzinfo or not now-timedelta(days=days) <= stamp <= now+timedelta(minutes=5):
                        continue
                except (ValueError, TypeError, OverflowError):
                    warnings.append('Message with invalid date skipped')
                    continue
                body = message.get_body(preferencelist=('plain', 'html'))
                body_text = plain(body.get_content()) if body else ''
                if len(body_text) > 8000:
                    warnings.append('Long message bodies truncated to 8000 characters')
                messages.append({'id': account['id']+':'+folder+':'+validity+':'+uid.decode(),
                    'message_id': str(message.get('Message-ID', '')), 'references': str(message.get('References', ''))+' '+str(message.get('In-Reply-To', '')),
                    'subject': str(message.get('Subject', ''))[:300], 'from': str(message.get('From', '')),
                    'to': str(message.get('To', '')), 'date': stamp.isoformat(), 'direction': direction,
                    'body': body_text[:8000], 'bulk': bool(message.get('List-Unsubscribe') or message.get('List-Id'))})
    if not readable_folders:
        raise RuntimeError('No readable mail folders')
    return {'messages': messages, 'warnings': sorted(set(warnings)), 'readable_folders': readable_folders}


def microsoft_app(account):
    import msal
    secret = secret_read(account['id'])
    cache = msal.SerializableTokenCache()
    if secret.get('cache'):
        cache.deserialize(secret['cache'])
    app = msal.PublicClientApplication(account['client_id'], authority='https://login.microsoftonline.com/common', token_cache=cache)
    return app, cache


def save_microsoft_cache(account, cache):
    secret_write(account['id'], {'cache': cache.serialize()})


def graph_mail(account, now, days=30, limit=100):
    import requests
    app, cache = microsoft_app(account)
    matches = app.get_accounts(username=account['username'])
    if not matches:
        raise ValueError('Microsoft sign-in required')
    token = app.acquire_token_silent(SCOPES, account=matches[0])
    save_microsoft_cache(account, cache)
    if not token or 'access_token' not in token:
        raise ValueError('Microsoft sign-in required')
    session = requests.Session()
    session.headers.update({'Authorization': 'Bearer '+token['access_token'], 'Prefer': 'outlook.body-content-type="text"'})
    messages, warnings = [], []
    cutoff = (now-timedelta(days=days)).astimezone(timezone.utc).isoformat()
    for folder, direction in [('inbox', 'inbox'), ('sentitems', 'sent')]:
        url = 'https://graph.microsoft.com/v1.0/me/mailFolders/'+folder+'/messages'
        datefield = 'sentDateTime' if direction == 'sent' else 'receivedDateTime'
        params = {'$top': '50', '$filter': datefield+' ge '+cutoff, '$orderby': datefield+' desc',
                  '$select': 'id,internetMessageId,conversationId,subject,from,toRecipients,receivedDateTime,sentDateTime,body,webLink,internetMessageHeaders'}
        count = 0
        while url and count < limit:
            if urlparse(url).netloc != 'graph.microsoft.com' or urlparse(url).scheme != 'https':
                raise ValueError('Invalid Microsoft pagination destination')
            response = session.get(url, params=params, timeout=25, allow_redirects=False)
            response.raise_for_status()
            payload = response.json()
            for item in payload.get('value', [])[:limit-count]:
                headers = {h['name'].lower(): h['value'] for h in item.get('internetMessageHeaders', [])}
                messages.append({'id': account['id']+':'+item['id'], 'message_id': item.get('internetMessageId', ''),
                    'references': headers.get('references', '')+' '+headers.get('in-reply-to', ''),
                    'conversation_id': item.get('conversationId'), 'subject': item.get('subject', ''),
                    'from': item.get('from', {}).get('emailAddress', {}).get('address', ''),
                    'to': ', '.join(x['emailAddress']['address'] for x in item.get('toRecipients', [])),
                    'date': item[datefield], 'direction': direction, 'body': plain(item.get('body', {}).get('content', ''))[:8000],
                    'url': item.get('webLink', ''), 'bulk': 'list-unsubscribe' in headers or 'list-id' in headers})
                count += 1
            url, params = payload.get('@odata.nextLink'), None
        if url:
            warnings.append(direction+' limited to latest '+str(limit)+' messages')
    return {'messages': messages, 'warnings': warnings}


def calendar_window(now, mode='weekly'):
    today = now.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    if mode == 'morning':
        return today, today + timedelta(days=7)
    if mode == 'evening':
        return today + timedelta(days=1), today + timedelta(days=2)
    if mode == 'weekly':
        return next_week(now)
    raise ValueError('Unknown review mode')


def calendar_events(account, now, mode='weekly'):
    import icalendar
    import recurring_ical_events
    warnings = []
    path = account.get('path')
    if path:
        source = Path(path)
        if source.stat().st_size > MAX_BYTES:
            raise ValueError('Calendar export too large')
        data = source.read_bytes()
        warnings.append('Local export last modified '+datetime.fromtimestamp(source.stat().st_mtime, TZ).isoformat()+'; refresh the export to see changes')
    else:
        import requests
        url = secret_read(account['id']).get('url', '')
        if urlparse(url).scheme != 'https':
            raise ValueError('HTTPS calendar link or local ICS file required')
        with requests.get(url, timeout=25, stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError('Calendar download failed')
            chunks, length = [], 0
            for chunk in response.iter_content(65536):
                length += len(chunk)
                if length > MAX_BYTES:
                    raise ValueError('Calendar too large')
                chunks.append(chunk)
            data = b''.join(chunks)
        warnings.append('Shared calendar feed can lag changes; confirm urgent changes in Proton Calendar')
    start, end = calendar_window(now, mode)
    calendar = icalendar.Calendar.from_ical(data)
    events = []
    for event in recurring_ical_events.of(calendar).between(start, end):
        if str(event.get('STATUS', '')).upper() == 'CANCELLED':
            continue
        beginning = event.decoded('DTSTART')
        all_day = isinstance(beginning, date) and not isinstance(beginning, datetime)
        if not all_day:
            beginning = beginning.replace(tzinfo=TZ) if beginning.tzinfo is None else beginning.astimezone(TZ)
        ending = event.decoded('DTEND') if event.get('DTEND') else None
        if isinstance(ending, datetime):
            ending = ending.replace(tzinfo=TZ) if ending.tzinfo is None else ending.astimezone(TZ)
        events.append({'uid': str(event.get('UID', '')), 'start': beginning.isoformat(), 'all_day': all_day,
                       'title': str(event.get('SUMMARY', 'Busy / no title')),
                       'location': str(event.get('LOCATION', '')), 'status': str(event.get('STATUS', '')),
                       'transparent': str(event.get('TRANSP', '')).upper() == 'TRANSPARENT',
                       'end': ending.isoformat() if ending and ending > beginning else None})
        if len(events) >= 500:
            warnings.append('Calendar limited to 500 occurrences')
            break
    if events and all(e['title'].strip().casefold() in ('busy', 'busy / no title', 'occupied', 'ocupado', 'private event', '') for e in events):
        warnings.append('Calendar exposes busy times only; full-view sharing is required for event titles')
    return {'events': sorted(events, key=lambda e: e['start']), 'warnings': warnings}


def drive_files(account, now):
    if not account.get('path', '').strip():
        raise ValueError('Select a local Proton Drive folder')
    root = Path(account['path']).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Select a local Proton Drive folder')
    files = []
    # Inventory only. Do not read document bodies or hydrate cloud-only files.
    count = 0
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(directory)/name).is_symlink()
                   and not (getattr((Path(directory)/name).lstat(), 'st_file_attributes', 0) & 0x400)]
        for name in names:
            count += 1
            path = Path(directory)/name
            if count > 1000:
                return {'files': files, 'warnings': ['Drive inventory limited to 1000 entries; document contents not read']}
            if path.is_symlink():
                continue
            stat = path.stat()
            changed = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            if changed >= now-timedelta(days=7):
                files.append({'name': str(path.relative_to(root)), 'modified': changed.isoformat()})
    return {'files': files, 'warnings': ['Local synced file inventory only; document contents not read']}


READERS = {'imap': imap_mail, 'gmail': imap_mail, 'icloud': imap_mail, 'bridge': imap_mail,
           'outlook': graph_mail, 'calendar': calendar_events, 'drive': drive_files}


def collect(config, now=None, mode='weekly'):
    now = now or datetime.now(timezone.utc)
    calendar_window(now, mode)  # Validate before contacting any source.
    def read(account):
        result = {k: account[k] for k in ('id', 'label', 'group', 'kind')}
        result.update(checked_at=now.isoformat(), status='not configured')
        if account.get('enabled'):
            try:
                reader = READERS[account['kind']]
                result.update(reader(account, now, mode=mode) if account['kind'] == 'calendar' else reader(account, now))
                result['status'] = 'ok'
            except Exception as error:
                # Never surface URLs, tokens, server responses or credentials.
                result.update(status='unavailable', error_type=type(error).__name__)
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(read, config['accounts']))
