"""Sort inbox email into the owner's own folders, asking on Telegram when unsure.

    python -m integrations.attention.organise status | run | pending | undo MOVE_ID

Sure means one of: the sender (or mailing list) is only ever filed in one folder, the owner answered
for that sender before, or the local model is at least `high_confidence` sure of an existing folder.
A new folder is created only when at least `organise_new_folder_min` emails in one run clearly need it.
Everything else becomes a question. Messages in a conversation with an open attention item, and
flagged messages, stay in the inbox. Every move is recorded and can be undone. Nothing is deleted,
marked read or sent anywhere except the questions to the owner's own Aurelius Telegram chat.
IMAP accounts only; Outlook needs write permission first (Mail.ReadWrite).
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
import json
import re
import sqlite3
import sys

from . import classify, config, sources, store

IMAP_KINDS = ('imap', 'gmail', 'icloud', 'bridge')
SKIP_FLAGS = {'\\noselect', '\\sent', '\\drafts', '\\trash', '\\junk', '\\all', '\\flagged', '\\important', '\\archive'}
SKIP_NAMES = {'inbox', 'sent', 'sent items', 'sent messages', 'drafts', 'trash', 'deleted items', 'deleted messages', 'junk',
              'junk e-mail', 'spam', 'outbox', 'archive', 'all mail', 'starred', 'important', 'enviados', 'borradores',
              'papelera', 'correo no deseado', 'notes', 'conversation history'}
SNIPPET = 600
LEARN_PER_FOLDER = 150
PROFILE_SUBJECTS = 3
CLAIM_MINUTES = 30

SCHEMA = '''
CREATE TABLE IF NOT EXISTS decisions(account TEXT, ref TEXT, message_id TEXT, sender TEXT, subject TEXT,
    status TEXT, folder TEXT, confidence REAL, reason TEXT, at TEXT, PRIMARY KEY(account, ref));
CREATE TABLE IF NOT EXISTS rules(account TEXT, key TEXT, folder TEXT, source TEXT, at TEXT, PRIMARY KEY(account, key));
CREATE TABLE IF NOT EXISTS moves(id INTEGER PRIMARY KEY, account TEXT, message_id TEXT, source TEXT, target TEXT,
    subject TEXT, at TEXT, undone_at TEXT);
CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY, account TEXT, ref TEXT, message_id TEXT, sender TEXT,
    subject TEXT, options TEXT, asked_at TEXT, answer TEXT, answered_at TEXT);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
'''

DECIDE = {
    'type': 'object',
    'properties': {
        'folder': {'type': ['string', 'null']},
        'new_folder': {'type': ['string', 'null']},
        'alternatives': {'type': 'array', 'items': {'type': 'string'}},
        'confidence': {'type': 'number'},
        'reason': {'type': 'string'},
    },
    'required': ['folder', 'new_folder', 'alternatives', 'confidence', 'reason'],
}

PROMPT = '''You file one email into the owner's existing mail folders. Answer with JSON only.
Folders (use the exact name): {folders}
{examples}
- folder: the existing folder this email belongs in, or null.
- new_folder: only when no folder fits and the email is clearly one of a recurring kind (a shop, a bank, a service,
  a project, an organisation): a short folder name in the language of the existing folders. Otherwise null.
- folder and new_folder are both null when the email should stay in the inbox: a personal conversation, something
  that needs a reply, or anything you cannot place.
- alternatives: up to two other existing folders that could fit, best first.
- confidence: 0 to 1 that your choice is what the owner would do. Below 0.85 the owner is asked.
- reason: a few words.'''


# --- storage -----------------------------------------------------------------------------------

@contextmanager
def connect(home=None):
    path = (home or config.home()) / 'system' / 'organise.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.executescript(SCHEMA)
        with db:
            yield db
    finally:
        db.close()


def claim(db, now: datetime) -> bool:
    """Only one sorting run at a time; a crashed run's claim lapses."""
    cursor = db.execute('''INSERT INTO meta(key,value) VALUES('claim',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value
                           WHERE meta.value<?''', ((now + timedelta(minutes=CLAIM_MINUTES)).isoformat(), now.isoformat()))
    db.commit()
    return cursor.rowcount == 1


def release(db) -> None:
    db.execute("DELETE FROM meta WHERE key='claim'")
    db.commit()


# --- IMAP --------------------------------------------------------------------------------------

def utf7_decode(name: str) -> str:
    """IMAP folder names use modified UTF-7 for anything outside ASCII."""
    def part(match):
        text = match.group(1)
        if not text:
            return '&'
        data = text.replace(',', '/')
        return base64.b64decode(data + '=' * (-len(data) % 4)).decode('utf-16-be')
    return re.sub(r'&([^-]*)-', part, name)


def utf7_encode(name: str) -> str:
    out, run = [], []

    def flush():
        if run:
            data = base64.b64encode(''.join(run).encode('utf-16-be')).decode().rstrip('=').replace('/', ',')
            out.append('&' + data + '-')
            run.clear()
    for char in name:
        if 0x20 <= ord(char) <= 0x7e:
            flush()
            out.append('&-' if char == '&' else char)
        else:
            run.append(char)
    flush()
    return ''.join(out)


def quote(name: str) -> str:
    return '"' + name.replace('\\', '\\\\').replace('"', '\\"') + '"'


def address(value: str) -> str:
    return sources.first_address(value)[1]


def rule_key(sender: str, list_id: str) -> str:
    found = re.search(r'<([^>]+)>', list_id or '')
    return 'list:' + found[1].casefold() if found else 'from:' + sender


class Mailbox:
    """One logged-in IMAP account. The fake in the tests has the same methods."""

    def __init__(self, account: dict):
        from integrations.msty.personal import connectors
        self.account = account
        self.client, password = connectors.imap_client(account)
        self.client.login(account['username'], password)
        self.selected = None
        status, caps = self.client.capability()
        self.can_move = b'MOVE' in b' '.join(caps or []).upper().split()

    def close(self):
        try:
            self.client.logout()
        except Exception:
            pass

    def folders(self) -> list[dict]:
        status, listing = self.client.list()
        found = []
        for row in listing or []:
            match = re.match(rb'\(([^)]*)\)\s+(?:"((?:[^"\\]|\\.)*)"|NIL)\s+(.+)$', row if isinstance(row, bytes) else b'')
            if match:
                raw = match[3].decode().strip()
                raw = raw[1:-1].replace('\\"', '"').replace('\\\\', '\\') if raw.startswith('"') else raw
                found.append({'raw': raw, 'name': utf7_decode(raw), 'delimiter': (match[2] or b'/').decode(),
                              'flags': {flag.casefold() for flag in match[1].decode().split()}})
        return found

    def select(self, raw: str, write=False):
        if self.selected not in ((raw, write), (raw, True)):  # a writable selection also serves reads
            status, data = self.client.select(quote(raw), readonly=not write)
            if status != 'OK':
                raise RuntimeError('Folder unavailable')
            self.selected = (raw, write)
            validity = self.client.response('UIDVALIDITY')[1]
            self.validity = validity[0].decode() if validity and validity[0] else 'unknown'

    def uids(self, raw: str) -> list[bytes]:
        self.select(raw)
        status, data = self.client.uid('search', None, 'ALL')
        return data[0].split() if status == 'OK' and data and data[0] else []

    def headers(self, raw: str, uid: bytes, fields='FROM LIST-ID') -> dict:
        self.select(raw)
        status, data = self.client.uid('fetch', uid, f'(FLAGS BODY.PEEK[HEADER.FIELDS ({fields})])')
        part = next((x for x in data or [] if isinstance(x, tuple)), None)
        if status != 'OK' or not part:
            return {}
        message = BytesParser(policy=policy.default).parsebytes(part[1], headersonly=True)
        result = {name.casefold(): str(message.get(name, '')) for name in fields.split()}
        result['flagged'] = b'\\Flagged' in part[0]
        return result

    def snippet(self, raw: str, uid: bytes) -> str:
        from integrations.msty.personal import connectors
        self.select(raw)
        status, data = self.client.uid('fetch', uid, '(BODY.PEEK[]<0.60000>)')
        part = next((x for x in data or [] if isinstance(x, tuple)), None)
        if status != 'OK' or not part:
            return ''
        try:
            body = BytesParser(policy=policy.default).parsebytes(part[1]).get_body(preferencelist=('plain', 'html'))
            return connectors.plain(body.get_content())[:SNIPPET] if body else ''
        except Exception:  # a cut-off multipart body is common; the headers still decide
            return ''

    def find(self, raw: str, message_id: str) -> bytes | None:
        self.select(raw)
        status, data = self.client.uid('search', None, 'HEADER', 'Message-ID', quote(message_id))
        found = data[0].split() if status == 'OK' and data and data[0] else []
        return found[-1] if found else None

    def move(self, source: str, uid: bytes, target: str) -> bool:
        if not self.can_move:
            raise RuntimeError('This mail server cannot move messages')
        self.select(source, write=True)
        status, _ = self.client.uid('MOVE', uid, quote(target))
        return status == 'OK'

    def create(self, raw: str) -> None:
        status, _ = self.client.create(quote(raw))
        if status != 'OK':
            raise RuntimeError('Folder could not be created')
        self.client.subscribe(quote(raw))


def candidates(account: dict, folders: list[dict]) -> list[dict]:
    """Folders the owner made for filing; system folders and Proton labels are never targets."""
    result = []
    for folder in folders:
        if folder['flags'] & SKIP_FLAGS or folder['name'].casefold() in SKIP_NAMES:
            continue
        if account['kind'] == 'bridge' and not folder['name'].startswith('Folders/'):
            continue
        if account['kind'] == 'gmail' and folder['name'].startswith('[Gmail]'):
            continue
        result.append(folder)
    return result


def display(account: dict, name: str) -> str:
    return name.removeprefix('Folders/') if account['kind'] == 'bridge' else name


def new_raw(account: dict, name: str, folders: list[dict]) -> str:
    name = re.sub(r'[\\/"%*]', ' ', name).strip()[:60]
    if not name:
        raise ValueError('Folder name is empty')
    prefix = 'Folders/' if account['kind'] == 'bridge' else ''
    return utf7_encode(prefix + name)


def learn(db, box, account: dict, targets: list[dict], now: datetime) -> None:
    """Senders and lists that are only ever filed in one folder become rules. Owner answers always win.
    Each folder also gets a profile (usual sender domains, recent subjects) that shows the model its pattern."""
    seen: dict[str, dict[str, int]] = {}
    profiles = {}
    for folder in targets:
        domains: dict[str, int] = {}
        subjects = []
        for uid in box.uids(folder['raw'])[-LEARN_PER_FOLDER:]:
            head = box.headers(folder['raw'], uid, 'FROM LIST-ID SUBJECT')
            sender = address(head.get('from', ''))
            if sender:
                counts = seen.setdefault(rule_key(sender, head.get('list-id', '')), {})
                counts[folder['raw']] = counts.get(folder['raw'], 0) + 1
                domain = sender.rsplit('@', 1)[-1]
                domains[domain] = domains.get(domain, 0) + 1
            if head.get('subject'):
                subjects.append(re.sub(r'\s+', ' ', head['subject'])[:80])
        profiles[folder['raw']] = {'domains': sorted(domains, key=domains.get, reverse=True)[:4],
                                   'subjects': subjects[-PROFILE_SUBJECTS:]}
    db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('profile:' + account['id'], json.dumps(profiles, ensure_ascii=False)))
    db.execute("DELETE FROM rules WHERE account=? AND source='folder'", (account['id'],))
    for key, counts in seen.items():
        if len(counts) == 1 and sum(counts.values()) >= 2:
            db.execute("INSERT OR IGNORE INTO rules VALUES(?,?,?,'folder',?)",
                       (account['id'], key, next(iter(counts)), now.isoformat()))
    db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('learned:' + account['id'], now.isoformat()))


def open_threads(account_id: str) -> set[str]:
    with store.connect() as db:
        rows = db.execute("SELECT thread_key FROM items WHERE channel='email' AND thread_key IS NOT NULL "
                          "AND state NOT IN ('COMPLETED','IGNORED','CANCELLED')").fetchall()
    return {row['thread_key'] for row in rows}


def thread_key(account_id: str, head: dict, ref: str) -> str:
    message = {'references': head.get('references', '') + ' ' + head.get('in-reply-to', ''),
               'message_id': head.get('message-id', ''), 'id': ref}
    return 'email:' + store.digest(account_id, sources.thread_root(message), length=16)


def decide(email: dict, targets: list[dict], account: dict, rules: dict, settings: dict, examples: str, *, post=None) -> dict:
    rule = rules.get(email['key'])
    names = {folder['raw']: display(account, folder['name']) for folder in targets}
    if rule in names:
        return {'action': 'move', 'folder': rule, 'confidence': 1.0, 'reason': 'you file this sender in ' + names[rule]}
    content = f'From: {email["from"]}\nSubject: {email["subject"]}\n' + \
        (f'Mailing list: {email["list_id"]}\n' if email['list_id'] else '') + f'\n{email["snippet"]}'
    messages = [{'role': 'system', 'content': PROMPT.format(folders=json.dumps(sorted(names.values()), ensure_ascii=False),
                                                            examples=examples)},
                {'role': 'user', 'content': content}]
    answer = json.loads(classify.chat(messages, settings, schema=DECIDE, **({'post': post} if post else {})))
    by_name = {name.casefold(): raw for raw, name in names.items()}
    folder = by_name.get(str(answer.get('folder') or '').casefold())
    new = str(answer.get('new_folder') or '').strip()[:60] or None
    if new and new.casefold() in by_name:
        folder, new = by_name[new.casefold()], None
    confidence = max(0.0, min(1.0, float(answer.get('confidence') or 0)))
    reason = str(answer.get('reason') or '')[:200]
    others = [by_name[a.casefold()] for a in answer.get('alternatives') or [] if isinstance(a, str) and a.casefold() in by_name]
    sure = confidence >= settings['high_confidence']
    if folder:
        return {'action': 'move' if sure else 'ask', 'folder': folder, 'others': others, 'confidence': confidence, 'reason': reason}
    if new:
        return {'action': 'new' if sure else 'ask', 'new': new, 'others': others, 'confidence': confidence, 'reason': reason}
    return {'action': 'keep' if sure else 'ask', 'others': others, 'confidence': confidence, 'reason': reason}


def examples_text(account: dict, targets: list[dict], rules: dict, profiles: dict) -> str:
    """What each folder already holds, so the model follows the owner's own filing patterns."""
    lines = []
    for folder in targets:
        profile = profiles.get(folder['raw']) or {}
        parts = []
        if profile.get('domains'):
            parts.append('usually from ' + ', '.join(profile['domains']))
        if profile.get('subjects'):
            parts.append('recent subjects: ' + ' | '.join(profile['subjects']))
        if not parts:
            keys = [key.split(':', 1)[1] for key, raw in rules.items() if raw == folder['raw']][:3]
            parts = ['e.g. ' + ', '.join(keys)] if keys else ['empty so far']
        lines.append(f'- {display(account, folder["name"])}: {"; ".join(parts)}')
    return ('What each folder holds now:\n' + '\n'.join(lines[:40])) if lines else ''


def record(db, account_id, email, status, folder, decision, now):
    db.execute('INSERT OR REPLACE INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?)',
               (account_id, email['ref'], email['message_id'], email['sender'], email['subject'], status, folder,
                decision.get('confidence'), decision.get('reason'), now.isoformat()))


def moved(db, account_id, email, source, target, now):
    db.execute('INSERT INTO moves(account,message_id,source,target,subject,at) VALUES(?,?,?,?,?,?)',
               (account_id, email['message_id'], source, target, email['subject'], now.isoformat()))


def sort_account(db, box, account: dict, settings: dict, now: datetime, budget: int, *, post=None) -> dict:
    folders = box.folders()
    inbox = next((f['raw'] for f in folders if f['name'].casefold() == 'inbox'), 'INBOX')
    targets = candidates(account, folders)
    learned = db.execute('SELECT value FROM meta WHERE key=?', ('learned:' + account['id'],)).fetchone()
    profiled = db.execute('SELECT 1 FROM meta WHERE key=?', ('profile:' + account['id'],)).fetchone()
    if not learned or not profiled or learned[0] < (now - timedelta(days=1)).isoformat():
        learn(db, box, account, targets, now)
    rules = {row['key']: row['folder'] for row in db.execute(
        "SELECT key,folder FROM rules WHERE account=? ORDER BY source='answer'", (account['id'],))}
    profiles = json.loads((db.execute('SELECT value FROM meta WHERE key=?', ('profile:' + account['id'],)).fetchone()
                           or ['{}'])[0])
    examples = examples_text(account, targets, rules, profiles)
    busy = open_threads(account['id'])
    done = {row['ref'] for row in db.execute('SELECT ref FROM decisions WHERE account=?', (account['id'],))}
    counts = {'moved': 0, 'kept': 0, 'asked': 0, 'held': 0, 'created': 0}
    groups: dict[str, list] = {}
    for uid in reversed(box.uids(inbox)):
        if budget <= 0:
            break
        ref = f'{box.validity}:{uid.decode()}'
        if ref in done:
            continue
        head = box.headers(inbox, uid, 'FROM SUBJECT LIST-ID MESSAGE-ID REFERENCES IN-REPLY-TO')
        if not head:
            continue
        budget -= 1
        sender = address(head.get('from', ''))
        email = {'ref': ref, 'uid': uid, 'message_id': head.get('message-id', '').strip(), 'sender': sender,
                 'from': head.get('from', '')[:200], 'subject': head.get('subject', '')[:200],
                 'list_id': head.get('list-id', '')[:200], 'key': rule_key(sender, head.get('list-id', ''))}
        if head.get('flagged') or thread_key(account['id'], head, ref) in busy or not email['message_id']:
            record(db, account['id'], email, 'held', None, {'reason': 'flagged, open attention item or no id'}, now)
            counts['held'] += 1
            continue
        email['snippet'] = '' if email['key'] in rules else box.snippet(inbox, uid)
        decision = decide(email, targets, account, rules, settings, examples, post=post)
        if decision['action'] == 'move':
            if box.move(inbox, uid, decision['folder']):
                moved(db, account['id'], email, inbox, decision['folder'], now)
                record(db, account['id'], email, 'moved', decision['folder'], decision, now)
                counts['moved'] += 1
        elif decision['action'] == 'keep':
            record(db, account['id'], email, 'kept', None, decision, now)
            counts['kept'] += 1
        elif decision['action'] == 'new':
            groups.setdefault(decision['new'].casefold(), []).append((email, decision))
        else:
            ask(db, account, email, decision, targets, now)
            counts['asked'] += 1
        db.commit()
    for group in groups.values():
        name = group[0][1]['new']
        if len(group) >= settings['organise_new_folder_min']:
            raw = new_raw(account, name, folders)
            box.create(raw)
            counts['created'] += 1
            for email, decision in group:
                if box.move(inbox, email['uid'], raw):
                    moved(db, account['id'], email, inbox, raw, now)
                    record(db, account['id'], email, 'moved', raw, decision, now)
                    counts['moved'] += 1
        else:
            for email, decision in group:
                ask(db, account, email, decision, targets, now)
                counts['asked'] += 1
        db.commit()
    return counts


def ask(db, account, email, decision, targets, now):
    names = {folder['raw']: display(account, folder['name']) for folder in targets}
    options = []
    if decision.get('folder'):
        options.append({'label': names[decision['folder']], 'raw': decision['folder']})
    if decision.get('new'):
        options.append({'label': 'New: ' + decision['new'], 'new': decision['new']})
    for raw in decision.get('others', []):
        if raw not in [o.get('raw') for o in options]:
            options.append({'label': names[raw], 'raw': raw})
    db.execute('INSERT INTO questions(account,ref,message_id,sender,subject,options) VALUES(?,?,?,?,?,?)',
               (account['id'], email['ref'], email['message_id'], email['sender'], email['subject'],
                json.dumps(options[:3], ensure_ascii=False)))
    record(db, account['id'], email, 'asked', None, decision, now)


# --- running -------------------------------------------------------------------------------------

def accounts(settings: dict) -> list[dict]:
    from integrations.msty.personal import store as connector_store
    found = [a for a in connector_store.load()['accounts'] if a.get('enabled') and a.get('kind') in IMAP_KINDS]
    if settings['organise_accounts']:
        found = [a for a in found if a['id'] in settings['organise_accounts']]
    return found


def run(*, settings=None, now=None, opener=Mailbox, notify=None, post=None, home=None) -> dict:
    settings = settings or config.load()
    now = now or datetime.now(timezone.utc)
    if not settings['organise_mail']:
        return {'status': 'off'}
    with connect(home) as db:
        if not claim(db, now):
            return {'status': 'busy'}
        try:
            result, chosen = {}, accounts(settings)
            share = max(1, settings['organise_per_run'] // max(1, len(chosen)))  # a big inbox must not starve the others
            for account in chosen:
                box = None
                try:
                    box = opener(account)
                    result[account['id']] = sort_account(db, box, account, settings, now, share, post=post)
                except classify.ModelUnavailable:
                    result[account['id']] = {'status': 'model unavailable'}
                    break
                except Exception as error:  # never surface server responses or credentials
                    result[account['id']] = {'status': 'unavailable', 'error_type': type(error).__name__}
                finally:
                    if box:
                        box.close()
            asked = (notify or telegram_questions)(db, settings['organise_questions_per_run'], now)
            return {'status': 'ok', 'accounts': result, 'questions_sent': asked}
        finally:
            release(db)


def pending(db=None, limit=50) -> list[dict]:
    def query(db):
        return [dict(row, options=json.loads(row['options'])) for row in db.execute(
            'SELECT id,account,sender,subject,options,asked_at FROM questions WHERE answer IS NULL ORDER BY id LIMIT ?', (limit,))]
    if db is not None:
        return query(db)
    with connect() as db:
        return query(db)


def telegram_questions(db, limit: int, now: datetime) -> int:
    """Send unasked questions to the owner's Aurelius chat, a few per run."""
    from integrations.msty.personal import interaction_store, publication
    rows = db.execute('SELECT * FROM questions WHERE answer IS NULL AND asked_at IS NULL ORDER BY id LIMIT ?', (limit,)).fetchall()
    if not rows:
        return 0
    route = publication.telegram_route()
    sent = 0
    for row in rows:
        options = json.loads(row['options'])
        buttons = [[(option['label'], 'file', {'q': row['id'], 'choice': index})] for index, option in enumerate(options)]
        buttons.append([('Keep in inbox', 'file', {'q': row['id'], 'choice': 'keep'})])
        markup = interaction_store.keyboard(route, buttons, now=now)
        text = f'Where should this email go? ({row["account"]})\nFrom: {row["sender"]}\nSubject: {row["subject"]}'
        if not options:
            text += '\nI could not suggest a folder. Tell me in Msty Go, or keep it in the inbox.'
        result = publication.telegram_call(route, 'sendMessage', {'chat_id': route['chat_id'], 'text': text,
                                                                   'reply_markup': markup})
        interaction_store.bind(route, markup, result['message_id'])
        db.execute('UPDATE questions SET asked_at=? WHERE id=?', (now.isoformat(), row['id']))
        db.commit()
        sent += 1
    return sent


def file(question_id: int, folder: str | None = None, *, choice=None, opener=Mailbox, now=None, settings=None, home=None) -> str:
    """Answer a question: an option index, 'keep', or a folder name (existing or new)."""
    settings = settings or config.load()
    now = now or datetime.now(timezone.utc)
    with connect(home) as db:
        row = db.execute('SELECT * FROM questions WHERE id=?', (int(question_id),)).fetchone()
        if not row:
            return 'That email question no longer exists.'
        if row['answer'] is not None:
            return f'Already answered: {row["answer"]}.'
        account = next((a for a in accounts(dict(settings, organise_accounts=[])) if a['id'] == row['account']), None)
        if not account:
            return 'That mail account is no longer available.'
        options = json.loads(row['options'])
        if choice == 'keep' or (folder or '').casefold() in ('keep', 'inbox', 'keep in inbox'):
            db.execute('UPDATE questions SET answer=?,answered_at=? WHERE id=?', ('kept in inbox', now.isoformat(), row['id']))
            db.execute("UPDATE decisions SET status='kept' WHERE account=? AND ref=?", (row['account'], row['ref']))
            return 'Kept in the inbox: ' + row['subject']
        option = options[int(choice)] if choice is not None and str(choice).isdigit() and int(choice) < len(options) else None
        box = opener(account)
        try:
            folders = box.folders()
            targets = candidates(account, folders)
            names = {display(account, f['name']).casefold(): f['raw'] for f in targets}
            wanted = (option or {}).get('raw') or names.get((folder or '').strip().casefold())
            new = (option or {}).get('new') or (None if wanted else (folder or '').strip())
            if not wanted and not new:
                return 'Tell me which folder.'
            if new:
                wanted = new_raw(account, new, folders)
                box.create(wanted)
            inbox = next((f['raw'] for f in folders if f['name'].casefold() == 'inbox'), 'INBOX')
            uid = box.find(inbox, row['message_id'])
            if uid is None:
                db.execute('UPDATE questions SET answer=?,answered_at=? WHERE id=?', ('no longer in inbox', now.isoformat(), row['id']))
                return 'That email is no longer in the inbox, so I left it where it is.'
            if not box.move(inbox, uid, wanted):
                return 'The mail server refused the move; nothing changed.'
            label = display(account, utf7_decode(wanted))
            email = {'message_id': row['message_id'], 'subject': row['subject'], 'ref': row['ref'], 'sender': row['sender']}
            moved(db, row['account'], email, inbox, wanted, now)
            db.execute("UPDATE decisions SET status='moved', folder=? WHERE account=? AND ref=?", (wanted, row['account'], row['ref']))
            db.execute("INSERT OR REPLACE INTO rules VALUES(?,?,?,'answer',?)",
                       (row['account'], 'from:' + row['sender'], wanted, now.isoformat()))
            db.execute('UPDATE questions SET answer=?,answered_at=? WHERE id=?', ('moved to ' + label, now.isoformat(), row['id']))
            return f'Moved to {label}: {row["subject"]}. I will file this sender there from now on.'
        finally:
            box.close()


def undo(move_id: int, *, opener=Mailbox, now=None, settings=None, home=None) -> str:
    settings = settings or config.load()
    now = now or datetime.now(timezone.utc)
    with connect(home) as db:
        row = db.execute('SELECT * FROM moves WHERE id=?', (int(move_id),)).fetchone()
        if not row or row['undone_at']:
            return 'Nothing to undo for that move.'
        account = next((a for a in accounts(dict(settings, organise_accounts=[])) if a['id'] == row['account']), None)
        if not account:
            return 'That mail account is no longer available.'
        box = opener(account)
        try:
            uid = box.find(row['target'], row['message_id'])
            if uid is None or not box.move(row['target'], uid, row['source']):
                return 'I could not find that email in the folder I moved it to.'
        finally:
            box.close()
        db.execute('UPDATE moves SET undone_at=? WHERE id=?', (now.isoformat(), row['id']))
        db.execute("DELETE FROM rules WHERE account=? AND source='answer' AND folder=? AND key=(SELECT 'from:'||sender "
                   "FROM decisions WHERE account=? AND message_id=? LIMIT 1)", (row['account'], row['target'], row['account'], row['message_id']))
        db.execute("UPDATE decisions SET status='kept', folder=NULL WHERE account=? AND message_id=?", (row['account'], row['message_id']))
        return 'Moved back to the inbox: ' + (row['subject'] or '(no subject)')


def status(home=None) -> dict:
    settings = config.load()
    with connect(home) as db:
        counts = {row['status']: row['n'] for row in db.execute('SELECT status, COUNT(*) n FROM decisions GROUP BY status')}
        recent = [dict(row) for row in db.execute(
            'SELECT id,account,subject,target,at FROM moves WHERE undone_at IS NULL ORDER BY id DESC LIMIT 10')]
        waiting = db.execute('SELECT COUNT(*) FROM questions WHERE answer IS NULL').fetchone()[0]
    for move in recent:
        move['target'] = utf7_decode(move['target']).removeprefix('Folders/')
    return {'enabled': settings['organise_mail'], 'decisions': counts, 'questions_open': waiting, 'recent_moves': recent}


def answer_button(payload: dict) -> str:
    """A Telegram button press from the owner's own chat (already authenticated by the relay)."""
    return file(int(payload['q']), choice=payload.get('choice'))


def main(argv=None) -> int:
    args = argv or sys.argv[1:] or ['status']
    if args[0] == 'run':
        result = run()
    elif args[0] == 'pending':
        result = pending()
    elif args[0] == 'undo' and len(args) == 2:
        result = undo(int(args[1]))
    elif args[0] == 'file' and len(args) == 3:
        result = file(int(args[1]), args[2])
    else:
        result = status()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
