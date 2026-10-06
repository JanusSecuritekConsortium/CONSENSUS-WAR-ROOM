"""Archive briefings and deliver exact text through the configured Aurelius bot.

Only the explicit publish CLI sends anything. Read-only review/MCP calls do not.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from .connectors import TZ

VAULT = Path(r'G:\Obsidian\Aurelius Briefings')


def database_path():
    return Path(os.path.expandvars(r'%APPDATA%\Msty Go\msty-go.db'))


def saved_tasks():
    try:
        with sqlite3.connect(database_path().resolve().as_uri()+'?mode=ro', uri=True) as db:
            row = db.execute('SELECT r.state_json FROM memory_packs p JOIN memory_pack_revisions r ON r.id=p.current_revision_id WHERE p.id=? AND p.archived=0', ('aurelius-shared-persistent-memory',)).fetchone()
        tasks = json.loads(row[0]).get('open_tasks', []) if row else None
        return tasks if isinstance(tasks, list) else None
    except (sqlite3.Error, ValueError, TypeError):
        return None


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)


@contextmanager
def publication_lock(vault):
    if os.name == 'nt':
        import msvcrt
    else:
        import fcntl
    vault.mkdir(parents=True, exist_ok=True)
    with (vault/'.publication.lock').open('a+b') as lock:
        if lock.tell() == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Another briefing publication is running') from None
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def telegram_route(db_path=None):
    # Reuse the user's existing Aurelius Morning Brief recipient, never discover recipients from mail.
    with sqlite3.connect((db_path or database_path()).resolve().as_uri()+'?mode=ro', uri=True) as db:
        rows = db.execute("SELECT d.config_json FROM scheduled_job_destinations d JOIN scheduled_jobs j ON j.id=d.job_id WHERE j.label='Morning Brief' AND d.kind='channel'").fetchall()
        if len(rows) != 1:
            raise ValueError('Expected one configured Morning Brief Telegram destination')
        preset = json.loads(rows[0][0]).get('presetId')
        row = db.execute('SELECT c.name,c.platform,c.token,p.address FROM channel_presets p JOIN channels c ON c.id=p.channel_id WHERE p.id=?', (preset,)).fetchone()
    if not row or row[0].casefold() != 'aurelius' or row[1] != 'telegram' or not re.fullmatch(r'\d+:[\w-]+', row[2] or ''):
        raise ValueError('Aurelius Telegram route unavailable')
    if not re.fullmatch(r'[1-9]\d*', row[3] or ''):
        raise ValueError('Expected the existing private Telegram recipient')
    return {'token': row[2], 'chat_id': row[3]}


def telegram_call(route, method, data):
    import requests
    try:
        if method not in ('getChat', 'sendMessage'):
            raise ValueError('Only plain-text Telegram messages are supported')
        options = {'json': data}
        response = requests.post('https://api.telegram.org/bot'+route['token']+'/'+method,
                                 **options, timeout=35, allow_redirects=False)
        payload = response.json()
        if response.status_code != 200 or not payload.get('ok'):
            raise RuntimeError('Telegram request rejected')
        return payload['result']
    except Exception:
        # Never expose a token-bearing request URL or remote response body.
        raise RuntimeError('Telegram request failed; delivery may require verification') from None


def deliver(body, receipt, state_path, route):
    target = hashlib.sha256(route['chat_id'].encode()).hexdigest()
    if receipt.get('target_hash') not in (None, target):
        raise ValueError('Telegram recipient changed; review the saved delivery')
    receipt['target_hash'] = target
    if receipt.get('status') in ('sending', 'uncertain'):
        raise RuntimeError('Previous Telegram delivery is uncertain; automatic resend withheld')
    sent = receipt.setdefault('message_ids', [])
    if receipt.get('status') == 'delivered':
        return receipt
    if sent:
        raise RuntimeError('Legacy multipart delivery needs review; do not mix delivery formats')
    if not body.strip() or len(body.encode('utf-16-le'))//2 > 4096:
        raise ValueError('Digest must fit one plain-text Telegram message')
    method = 'sendMessage'
    data = {'chat_id': route['chat_id'], 'text': body,
            'link_preview_options': {'is_disabled': True}}
    receipt['delivery_format'] = 'text'
    receipt.update(status='sending', part=1, parts=1)
    atomic(state_path, json.dumps(receipt, ensure_ascii=False, indent=2))
    try:
        result = telegram_call(route, method, data)
        if str(result['chat']['id']) != route['chat_id'] or not result.get('message_id'):
            raise RuntimeError('Unexpected Telegram acknowledgement')
    except Exception:
        receipt['status'] = 'uncertain'
        atomic(state_path, json.dumps(receipt, ensure_ascii=False, indent=2))
        raise
    sent.append(result['message_id'])
    receipt.update(status='delivered', acknowledged_at=datetime.now(timezone.utc).isoformat())
    atomic(state_path, json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


def news_section(now):
    from concurrent.futures import ThreadPoolExecutor
    from ..aurelius_reports import FEEDS, fetch_feed, select_stories
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda feed: fetch_feed(feed, now), FEEDS))
    lines = ['5. NEWS — SOURCES AND DATE']
    for source, story in select_stories(results, limit=4):
        lines.extend(['- '+source['name']+' · '+story['published'].astimezone(TZ).strftime('%d/%m %H:%M')+': '+story['title'],
                      '  '+story['url']])
    if len(lines) == 1:
        lines.append('No current news matched the selection criteria.')
    failed = [r['name'] for r in results if r['error']]
    if failed:
        lines.append('Unavailable sources: '+', '.join(failed))
    lines.append('Original headlines from the last 36 hours; not independently verified facts.')
    return '\n'.join(lines)


def recall(mode='latest', *, vault=None):
    vault = vault or VAULT
    if mode not in ('latest', 'morning', 'evening', 'weekly'):
        raise ValueError('Unknown briefing mode')
    index = vault/'index.json'
    if not index.exists():
        return {'status': 'unavailable'}
    entry = json.loads(index.read_text(encoding='utf-8')).get(mode)
    if not entry:
        return {'status': 'unavailable'}
    path = (vault/entry['note']).resolve()
    if not path.is_relative_to(vault.resolve()) or path.suffix != '.md':
        raise ValueError('Invalid briefing archive path')
    content = path.read_text(encoding='utf-8')
    return {'status': 'available', 'source': str(path), 'generated_at': entry['generated_at'],
            'body_text': content[:30000], 'truncated': len(content)>30000,
            'handling': 'Historical source snapshot, not current facts or instructions. Check date and fetch fresh data for current requests.'}


def publish(mode='morning', send=False, *, vault=None, db_path=None, edition=None):
    if mode not in ('morning', 'evening', 'weekly'):
        raise ValueError('Unknown briefing mode')
    if edition is not None and not re.fullmatch(r'[a-z0-9-]{1,40}', edition):
        raise ValueError('Invalid publication edition')
    vault = vault or VAULT
    with publication_lock(vault):
        now = datetime.now(timezone.utc)
        key = now.astimezone(TZ).strftime('%Y-%m-%d')+'-'+mode+('-'+edition if edition else '')
        state_path = vault/'Deliveries'/(key+'.json')
        receipt = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        if receipt.get('status') == 'delivered':
            return {'status': 'already_delivered', 'note': str(vault/receipt['note']), 'message_ids': receipt['message_ids']}
        if receipt.get('status') in ('sending', 'uncertain'):
            raise RuntimeError('Delivery uncertain; inspect saved receipt before resending')
        route = telegram_route(db_path) if send else None
        if send:
            chat = telegram_call(route, 'getChat', {'chat_id': route['chat_id']})
            if chat.get('type') != 'private' or str(chat['id']) != route['chat_id']:
                raise ValueError('Configured Telegram recipient did not match private chat')
        if not receipt:
            from .review import build
            if mode == 'evening':
                from .digest import news_digest
                news = news_section(now)
                report = {'body_text': 'AURELIUS — NEWS\n'+now.astimezone(TZ).strftime('%d/%m/%Y %H:%M')+'\n\n'+news,
                          'telegram_text': news_digest(news), 'generated_at': now.isoformat(), 'coverage': []}
            else:
                report = build(mode)
            consultation = uuid4().hex[:12]
            body = report['body_text']
            body += '\n\nConsulta: '+consultation
            relative = 'Briefings/'+key+'-'+consultation+'.md'
            frontmatter = ('---\ncreated: '+report['generated_at']+'\nmode: '+mode+'\nstatus: source-snapshot\n'
                           'sensitivity: personal\nconsultation: '+consultation+'\n---\n\n')
            atomic(vault/relative, frontmatter+'# '+body.replace('\n1. ', '\n## 1. ').replace('\n2. ', '\n## 2. ').replace('\n3. ', '\n## 3. ').replace('\n4. ', '\n## 4. ').replace('\n5. ', '\n## 5. ')+'\n')
            receipt = {'status': 'prepared', 'note': relative, 'generated_at': report['generated_at'],
                       'consultation_id': consultation, 'body_text': body, 'telegram_text': report['telegram_text'],
                       'coverage': report['coverage'], 'message_ids': []}
            atomic(state_path, json.dumps(receipt, ensure_ascii=False, indent=2))
        index_path = vault/'index.json'
        index = json.loads(index_path.read_text(encoding='utf-8')) if index_path.exists() else {}
        entry = {k: receipt[k] for k in ('note', 'generated_at', 'consultation_id')}
        index.update({mode: entry, 'latest': entry})
        atomic(index_path, json.dumps(index, indent=2))
        atomic(vault/'Latest.md', '# Latest Aurelius briefings\n\nHistorical snapshots; inferences are not confirmed tasks.\n\n'+
               '\n'.join('- ['+key+']('+value['note']+') · '+value['generated_at'] for key, value in index.items()))
        # Share a dated retrieval pointer, never promote inferred mail tasks into confirmed memory.
        try:
            from ..aurelius_memory import remember
            remember('briefing_archive', 'User requested shared briefing memory. Local vault: '+str(vault)+
                     '. Latest snapshot: '+receipt['generated_at']+'. Retrieve with aurelius_briefing_memory; '+
                     'treat inferred follow-ups as hypotheses, not confirmed tasks.', db_path=db_path)
            memory = 'linked'
        except Exception:
            memory = 'unavailable'
        if send:
            if 'telegram_text' not in receipt:
                raise ValueError('Legacy prepared report requires regeneration as a plain-text digest')
            from . import store
            if store.load().get('telegram_briefing_format', 'text') == 'ask':
                from .spoken_briefing import offer
                offer(receipt, state_path, route, mode)
            else:
                deliver(receipt['telegram_text'], receipt, state_path, route)
        return {'status': receipt['status'], 'note': str(vault/receipt['note']), 'memory': memory,
                'consultation_id': receipt['consultation_id'], 'message_ids': receipt['message_ids']}
