"""Private durable button bindings, conversation language and reminder controls."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
import sqlite3
from . import store
from .connectors import TZ


def owner(route):
    return hashlib.sha256(str(route['chat_id']).encode()).hexdigest()


def database():
    store.ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(store.ROOT/'interactions.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS buttons(token TEXT PRIMARY KEY, owner TEXT,
            message_id INTEGER, action TEXT, payload TEXT, expires TEXT);
        CREATE TABLE IF NOT EXISTS languages(owner TEXT PRIMARY KEY, language TEXT);
        CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, payload TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS controls(id TEXT PRIMARY KEY, state TEXT, until_date TEXT);
        CREATE TABLE IF NOT EXISTS selections(owner TEXT, message_id INTEGER, ids TEXT,
            PRIMARY KEY(owner,message_id));
        CREATE TABLE IF NOT EXISTS mutations(request_key TEXT PRIMARY KEY, result TEXT);
    ''')
    return db


def language(route, value=None):
    with database() as db:
        if value in ('en', 'es'):
            db.execute('INSERT OR REPLACE INTO languages VALUES (?,?)', (owner(route), value))
            return value
        row = db.execute('SELECT language FROM languages WHERE owner=?', (owner(route),)).fetchone()
        return row[0] if row else 'en'


def keyboard(route, rows, *, now=None):
    """Persist opaque callback tokens before a send; bind after acknowledgement."""
    now = now or datetime.now(timezone.utc)
    result = []
    with database() as db:
        db.execute('DELETE FROM buttons WHERE expires<?', (now.isoformat(),))
        for row in rows:
            buttons = []
            for label, action, payload in row:
                token = 'au:'+secrets.token_hex(12)
                db.execute('INSERT INTO buttons VALUES (?,?,NULL,?,?,?)',
                           (token, owner(route), action, json.dumps(payload),
                            (now+timedelta(hours=18)).isoformat()))
                buttons.append({'text': label, 'callback_data': token})
            result.append(buttons)
    return {'inline_keyboard': result}


def bind(route, markup, message_id, ids=()):
    with database() as db:
        for row in markup.get('inline_keyboard', []):
            for button in row:
                db.execute('UPDATE buttons SET message_id=? WHERE token=? AND owner=? AND message_id IS NULL',
                           (message_id, button.get('callback_data'), owner(route)))
        if ids:
            db.execute('INSERT OR REPLACE INTO selections VALUES (?,?,?)',
                       (owner(route), message_id, json.dumps(list(ids))))


def resolve(route, callback, *, now=None):
    now = now or datetime.now(timezone.utc)
    message = callback.get('message', {})
    if (str(callback.get('from', {}).get('id')) != str(route['chat_id'])
            or callback.get('from', {}).get('is_bot')
            or message.get('chat', {}).get('type') != 'private'
            or str(message.get('chat', {}).get('id')) != str(route['chat_id'])):
        return None
    with database() as db:
        row = db.execute('SELECT * FROM buttons WHERE token=? AND owner=? AND message_id=? AND expires>?',
                         (callback.get('data'), owner(route), message.get('message_id'), now.isoformat())).fetchone()
    return (row['action'], json.loads(row['payload'])) if row else None


def selected(route, message_id):
    with database() as db:
        row = db.execute('SELECT ids FROM selections WHERE owner=? AND message_id=?',
                         (owner(route), message_id)).fetchone()
    return json.loads(row[0]) if row else []


def item_id(kind, identity):
    return hashlib.sha256((kind+'\0'+identity).encode()).hexdigest()


def register(items, now):
    with database() as db:
        for item in items:
            db.execute('INSERT OR REPLACE INTO items VALUES (?,?,?)',
                       (item['id'], json.dumps(item, ensure_ascii=False), now.isoformat()))


def visible(identity, now):
    with database() as db:
        row = db.execute('SELECT state,until_date FROM controls WHERE id=?', (identity,)).fetchone()
    return not row or (row[0] != 'handled' and now.astimezone(TZ).date().isoformat() >= row[1])


def mutate(identity, action, request_key, now, lang):
    from .language import choose
    with database() as db:
        prior = db.execute('SELECT result FROM mutations WHERE request_key=?', (request_key,)).fetchone()
        if prior:
            return prior[0]
        row = db.execute('SELECT payload FROM items WHERE id=?', (identity,)).fetchone()
        if not row or action not in ('handled', 'tomorrow'):
            return choose(lang, 'That follow-up is no longer available.', 'Ese seguimiento ya no está disponible.')
        title = json.loads(row[0])['title']
        if action == 'handled':
            result = choose(lang, 'I will stop reminding you about: ', 'Dejaré de recordarte: ')+title
            until = ''
        else:
            until = (now.astimezone(TZ).date()+timedelta(days=1)).isoformat()
            result = choose(lang, 'Deferred until tomorrow’s briefing: ', 'Pospuesto hasta el informe de mañana: ')+title
        db.execute('INSERT OR REPLACE INTO controls VALUES (?,?,?)', (identity, action, until))
        db.execute('INSERT INTO mutations VALUES (?,?)', (request_key, result))
    return result
