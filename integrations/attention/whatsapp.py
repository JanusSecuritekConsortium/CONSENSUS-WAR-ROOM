r"""Read-only WhatsApp personal chats through a linked device, the way WhatsApp Web is linked.

    .venv-whatsapp\Scripts\python.exe -m integrations.attention.whatsapp pair    # QR code: WhatsApp > Linked devices > Link a device
    .venv-whatsapp\Scripts\python.exe -m integrations.attention.whatsapp listen  # keeps the local copy current; meant to run at sign-in
    .venv-whatsapp\Scripts\python.exe -m integrations.attention.whatsapp forget  # unlink this device and delete the local copy
    python -m integrations.attention.whatsapp status

WhatsApp refuses old clients, and current neonize needs Python 3.11 or newer, so pairing and the
listener run from their own environment (requirements-whatsapp.txt). The scan only reads the
SQLite copy and needs neither neonize nor that environment.

WhatsApp has no official way to read your own chats, so this uses an unofficial client (neonize,
built on whatsmeow). Linking one is against WhatsApp's terms and can, rarely, get a number
restricted; reading only is the lowest-risk use. This module never sends, never marks anything
read and never shows presence. If WhatsApp logs the device out or restricts it, the listener
stops and stays stopped until the user pairs again.

WhatsApp delivers messages to a linked device as they arrive, plus a one-off history sync at
pairing, so `listen` stores one-to-one text messages (no groups, status or channels, no media
files) in a private SQLite copy for KEEP_DAYS. The attention scan reads that copy.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import logging
import sqlite3
import sys
import threading

from integrations.msty.personal import store as accounts

FOLDER = accounts.ROOT / 'whatsapp'
SESSION = FOLDER / 'device.sqlite3'      # neonize's own device keys
MESSAGES = FOLDER / 'messages.sqlite3'   # the local copy the scan reads
LOCK = FOLDER / 'listener.lock'
KEEP_DAYS = 90
STALE_AFTER = timedelta(minutes=30)
PERSONAL_SERVERS = ('s.whatsapp.net', 'lid')
STOPPED = ('logged_out', 'temporarily_banned')
_write = threading.Lock()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def connect() -> sqlite3.Connection:
    FOLDER.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(MESSAGES, timeout=30, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS chats(jid TEXT PRIMARY KEY, phone TEXT, name TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS messages(chat TEXT, id TEXT, from_me INTEGER, at TEXT, text TEXT,
                                            PRIMARY KEY(chat, id));
        CREATE INDEX IF NOT EXISTS messages_at ON messages(at);
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);''')
    return db


def meta(key: str, default=None):
    if not MESSAGES.exists():
        return default
    with closing(connect()) as db:
        row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
    return row['value'] if row else default


def set_meta(**values) -> None:
    with _write, closing(connect()) as db:
        db.executemany('INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                       list(values.items()))
        db.commit()


def configured() -> bool:
    return meta('state') == 'linked'


# ---- turning WhatsApp events into rows -------------------------------------------------------

def jid_text(jid) -> str:
    return f'{jid.User}@{jid.Server}' if jid.User else ''


def personal(jid_string: str) -> bool:
    user, _, server = jid_string.partition('@')
    return bool(user) and server in PERSONAL_SERVERS


def phone_of(jid_string: str) -> str:
    user, _, server = jid_string.partition('@')
    return '+' + user.split(':')[0] if server == 's.whatsapp.net' and user else ''


def text_of(message) -> str | None:
    """Readable text of a message, a short label for media, None for reactions, edits and protocol traffic."""
    for wrapper in ('ephemeralMessage', 'viewOnceMessage'):
        if message.HasField(wrapper):
            return text_of(getattr(message, wrapper).message)
    if message.conversation:
        return message.conversation
    if message.HasField('extendedTextMessage'):
        return message.extendedTextMessage.text or None
    if message.HasField('imageMessage'):
        return message.imageMessage.caption or '(photo)'
    if message.HasField('videoMessage'):
        return message.videoMessage.caption or '(video)'
    if message.HasField('audioMessage'):
        return '(voice note)' if message.audioMessage.PTT else '(audio)'
    if message.HasField('documentMessage'):
        return message.documentMessage.caption or '(file)'
    return None


def stamp(seconds: int) -> str:
    seconds = int(seconds)
    if seconds > 100_000_000_000:  # milliseconds
        seconds //= 1000
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def save(rows: list[tuple], chats: list[tuple]) -> None:
    """rows: (chat, id, from_me, at, text); chats: (jid, phone, name). Known values are never blanked."""
    if not rows and not chats:
        return
    now = utcnow().isoformat()
    with _write, closing(connect()) as db:
        db.executemany('''INSERT INTO chats VALUES(?,?,?,?) ON CONFLICT(jid) DO UPDATE SET
                          phone=COALESCE(NULLIF(excluded.phone,''), chats.phone),
                          name=COALESCE(NULLIF(excluded.name,''), chats.name), updated_at=excluded.updated_at''',
                       [(jid, phone, name, now) for jid, phone, name in chats])
        db.executemany('INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?)', rows)
        db.execute('DELETE FROM messages WHERE at < ?', ((utcnow() - timedelta(days=KEEP_DAYS)).isoformat(),))
        db.execute('INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', ('heartbeat', now))
        db.commit()


def live_message(event) -> None:
    source = event.Info.MessageSource
    chat = jid_text(source.Chat)
    if source.IsGroup or not personal(chat):
        return
    text = text_of(event.Message)
    if text is None:
        return
    alternative = jid_text(source.RecipientAlt if source.IsFromMe else source.SenderAlt)
    phone = phone_of(chat) or phone_of(alternative)
    name = '' if source.IsFromMe else event.Info.Pushname
    save([(chat, event.Info.ID, int(source.IsFromMe), stamp(event.Info.Timestamp), text)], [(chat, phone, name)])


def history(event) -> None:
    data = event.Data
    names = {item.ID: item.pushname for item in data.pushnames}
    phones = {item.lidJID: phone_of(item.pnJID) for item in data.phoneNumberToLidMappings}
    rows, chats = [], []
    for conversation in data.conversations:
        chat = conversation.ID
        if not personal(chat):
            continue
        phone = phone_of(chat) or phone_of(conversation.pnJID) or phones.get(chat, '')
        chats.append((chat, phone, conversation.name or conversation.displayName or names.get(chat, '')))
        for item in conversation.messages:
            info = item.message
            text = text_of(info.message)
            if text is not None and info.key.ID:
                rows.append((chat, info.key.ID, int(info.key.fromMe), stamp(info.messageTimestamp), text))
    save(rows, chats)


# ---- the scan's reader -----------------------------------------------------------------------

def fetch(now, days: int, limit: int):
    since = (now - timedelta(days=days)).isoformat()
    with closing(connect()) as db:
        state = dict(db.execute('SELECT key, value FROM meta'))
        chats = []
        for row in db.execute('SELECT c.jid, c.phone, c.name FROM chats c WHERE EXISTS '
                              '(SELECT 1 FROM messages m WHERE m.chat=c.jid AND m.at >= ?)', (since,)):
            messages = db.execute('SELECT id, from_me, at, text FROM messages WHERE chat=? AND at >= ? '
                                  'ORDER BY at DESC, rowid DESC LIMIT ?', (row['jid'], since, limit)).fetchall()
            chats.append({'chat': row['jid'], 'address': row['phone'] or 'whatsapp:' + row['jid'].split('@')[0],
                          'name': row['name'] or '',
                          'messages': [{'id': m['id'], 'from_me': bool(m['from_me']), 'at': m['at'], 'text': m['text']}
                                       for m in reversed(messages)]})
    heartbeat = state.get('heartbeat')
    if state.get('state') in STOPPED:
        status = {'status': 'unavailable', 'error_type': state['state']}
    elif not heartbeat or now - datetime.fromisoformat(heartbeat) > STALE_AFTER:
        status = {'status': 'stale', 'error_type': 'ListenerNotRunning'}  # the stored copy is still used
    else:
        status = {'status': 'ok'}
    return chats, dict(status, chats=len(chats))


# ---- the linked device -----------------------------------------------------------------------

def _lock_without_waiting(handle) -> None:
    """Lock the first byte of an open file, or raise OSError if another process holds it."""
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.lockf(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB, 1)


class SingleInstance:
    def __enter__(self):
        FOLDER.mkdir(parents=True, exist_ok=True)
        self.handle = open(LOCK, 'a+')
        try:
            _lock_without_waiting(self.handle)
        except OSError:
            self.handle.close()
            raise RuntimeError('Another WhatsApp listener is already running') from None
        return self

    def __exit__(self, *exc):
        self.handle.close()


def device(on_qr=None, on_paired=None):
    from neonize.client import NewClient
    from neonize.events import (ConnectedEv, HistorySyncEv, LoggedOutEv, MessageEv, PairStatusEv,
                                StreamReplacedEv, TemporaryBanEv)
    from neonize.proto.waCompanionReg.WAWebProtobufsCompanionReg_pb2 import DeviceProps
    logging.getLogger('whatsmeow').setLevel(logging.WARNING)
    logging.getLogger('neonize').setLevel(logging.WARNING)
    client = NewClient(str(SESSION), props=DeviceProps(os='Aurelius (read-only)', platformType=DeviceProps.DESKTOP))

    def guarded(handler):
        def run(_client, event):
            try:
                handler(event)
            except Exception as error:  # one bad event must not stop the listener
                set_meta(last_error=f'{type(error).__name__} at {utcnow().isoformat()}')
        return run

    def stop(state):
        def handler(_event):
            set_meta(state=state, stopped_at=utcnow().isoformat())
            client.disconnect()
        return handler

    def paired(event):
        if event.Error:
            set_meta(last_error=f'pairing failed at {utcnow().isoformat()}')
            return
        set_meta(state='linked', paired_at=utcnow().isoformat())
        if on_paired:
            on_paired()

    client.event(MessageEv)(guarded(live_message))
    client.event(HistorySyncEv)(guarded(history))
    client.event(ConnectedEv)(guarded(lambda event: set_meta(heartbeat=utcnow().isoformat(), connected_at=utcnow().isoformat())))
    client.event(PairStatusEv)(guarded(paired))
    client.event(LoggedOutEv)(guarded(stop('logged_out')))
    client.event(TemporaryBanEv)(guarded(stop('temporarily_banned')))
    client.event(StreamReplacedEv)(guarded(lambda event: client.disconnect()))
    if on_qr:
        client.event.qr(lambda _client, code: on_qr(code))
    return client


def heartbeat(client, stop: threading.Event) -> None:
    while not stop.wait(300):
        try:
            if client.is_connected:
                set_meta(heartbeat=utcnow().isoformat())
        except Exception:
            pass


def listen() -> str:
    if not configured():
        return f'not linked ({meta("state", "never paired")}): run python -m integrations.attention.whatsapp pair'
    with SingleInstance():
        def lost(_code):  # WhatsApp asking for a QR here means the link was removed
            set_meta(state='logged_out', stopped_at=utcnow().isoformat())
            client.disconnect()
        client = device(on_qr=lost)
        stop = threading.Event()
        threading.Thread(target=heartbeat, args=(client, stop), daemon=True).start()
        try:
            client.connect()
        finally:
            stop.set()
    return f'listener stopped ({meta("state")})'


def pair_window() -> None:
    import base64
    import io
    import queue
    import tkinter as tk
    from tkinter import ttk
    import segno

    events = queue.Queue()
    root = tk.Tk()
    root.title('Aurelius — link WhatsApp (read-only)')
    frame = ttk.Frame(root, padding=16)
    frame.grid()
    ttk.Label(frame, wraplength=380, justify='left', text=(
        'On your phone: WhatsApp → Settings → Linked devices → Link a device, then scan this code.\n'
        'Aurelius only reads your one-to-one chats; it never sends or marks anything as read. '
        'This is an unofficial client: WhatsApp does not allow it, and rarely restricts numbers that use one.'
    )).grid(sticky='w')
    picture = ttk.Label(frame)
    picture.grid(pady=10)
    message = tk.StringVar(value='Waiting for a code from WhatsApp…')
    ttk.Label(frame, textvariable=message, wraplength=380, foreground='#555').grid(sticky='w')

    def show(code: bytes):
        buffer = io.BytesIO()
        segno.make(code.decode(), error='l').save(buffer, kind='png', scale=6, border=2)
        image = tk.PhotoImage(data=base64.b64encode(buffer.getvalue()))
        picture.configure(image=image)
        picture.image = image
        message.set('Scan the code. A new one appears every 20 seconds or so.')

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == 'qr':
                    show(value)
                elif kind == 'paired':
                    picture.configure(image='')
                    message.set('Linked. Close this window. Your recent chats arrive when the listener starts, '
                                'and it keeps the copy current from then on.')
                elif kind == 'stopped':
                    message.set(value)
        except queue.Empty:
            pass
        root.after(300, poll)

    try:
        lock = SingleInstance().__enter__()
    except RuntimeError:
        message.set('The listener is running, so WhatsApp is already linked. Use forget first to link again.')
        root.mainloop()
        return
    set_meta(state='pairing')
    client = device(on_qr=lambda code: events.put(('qr', code)), on_paired=lambda: events.put(('paired', None)))

    def run():
        try:
            client.connect()
        except Exception as error:
            events.put(('stopped', f'WhatsApp connection failed ({type(error).__name__}).'))
    threading.Thread(target=run, daemon=True).start()
    root.after(300, poll)

    def no_code():
        if picture.image is None and meta('state') == 'pairing':
            message.set('WhatsApp has not sent a code. It may be refusing this client version: '
                        'update neonize in .venv-whatsapp and try again.')
    picture.image = None
    root.after(30_000, no_code)
    root.lift()
    root.attributes('-topmost', True)
    root.after(800, lambda: root.attributes('-topmost', False))
    try:
        root.mainloop()
    finally:
        try:
            client.disconnect()
        finally:
            lock.__exit__()
            if meta('state') == 'pairing':
                set_meta(state='never paired')


def forget() -> str:
    try:
        with SingleInstance():
            if configured():
                try:
                    device().logout()
                except Exception:
                    pass  # it can also be removed on the phone under Linked devices
            for path in (SESSION, MESSAGES):
                if path.exists():
                    path.unlink()
    except RuntimeError as error:
        return f'{error}; stop it first.'
    return 'WhatsApp unlinked and the local copy deleted.'


def status_text() -> str:
    if not MESSAGES.exists():
        return 'not set up: python -m integrations.attention.whatsapp pair'
    with closing(connect()) as db:
        state = dict(db.execute('SELECT key, value FROM meta'))
        chats = db.execute('SELECT COUNT(DISTINCT chat) FROM messages').fetchone()[0]
    return f'{state.get("state", "unknown")}, {chats} chats stored, last heartbeat {state.get("heartbeat", "never")}'


def main(argv=None) -> int:
    command = (argv or sys.argv[1:] or ['status'])[0]
    if command in ('pair', 'listen', 'forget') and sys.version_info < (3, 11):
        print(r'Run this with .venv-whatsapp\Scripts\python.exe: WhatsApp refuses the neonize version that fits this Python.')
        return 2
    if command == 'pair':
        pair_window()
    elif command == 'listen':
        print(listen())
    elif command == 'forget':
        print(forget())
    elif command == 'status':
        print(status_text())
    else:
        print('usage: pair | listen | status | forget')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
