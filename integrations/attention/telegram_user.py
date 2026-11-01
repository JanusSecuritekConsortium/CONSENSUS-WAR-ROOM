"""Read-only Telegram personal chats through the user's own account (Telegram's user API).

    python -m integrations.attention.telegram_user setup     # local sign-in window; the user types everything
    python -m integrations.attention.telegram_user status
    python -m integrations.attention.telegram_user forget    # sign this reader out and delete its session

Only one-to-one chats with people are read: no groups, channels, bots or Telegram's own notices.
Nothing is sent and nothing is marked as read. The api_id/api_hash and the signed-in session are
kept together with Windows DPAPI in the private Aurelius folder, never in the repository or the vault.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
import sys
import threading

from integrations.msty.personal import store as accounts

SECRET = 'telegram-user'
SERVICE_USERS = {777000, 42777}  # Telegram notifications and the Telegram service account
DIALOG_LIMIT = 200
DEVICE = {'device_model': 'Aurelius attention reader (read-only)', 'system_version': 'Windows', 'app_version': '1.0'}


class NotSignedIn(RuntimeError):
    pass


def credentials() -> dict:
    try:
        return accounts.secret_read(SECRET)
    except Exception:  # unreadable for this Windows user: treat as not set up
        return {}


def configured() -> bool:
    return bool(credentials().get('session'))


def client(creds: dict, session: str = ''):
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    return TelegramClient(StringSession(session), int(creds['api_id']), creds['api_hash'], receive_updates=False, **DEVICE)


def in_thread(coroutine_factory):
    """Run a coroutine on its own loop, so callers inside an event loop (the MCP server) are unaffected."""
    outcome = {}

    def target():
        try:
            outcome['value'] = asyncio.run(coroutine_factory())
        except BaseException as error:
            outcome['error'] = error
    worker = threading.Thread(target=target, name='telegram-reader', daemon=True)
    worker.start()
    worker.join(timeout=600)
    if worker.is_alive():
        raise TimeoutError('Telegram read did not finish')
    if 'error' in outcome:
        raise outcome['error']
    return outcome['value']


def text_of(message) -> str | None:
    if message.action:  # joins, calls, pinned notices
        return None
    if message.message:
        return message.message
    for attribute, label in (('voice', '(voice note)'), ('video_note', '(video note)'), ('photo', '(photo)'),
                             ('video', '(video)'), ('sticker', '(sticker)'), ('gif', '(gif)'),
                             ('contact', '(contact card)'), ('geo', '(location)'), ('poll', '(poll)'),
                             ('document', '(file)')):
        if getattr(message, attribute, None):
            return label
    return None


def address(user) -> str:
    if user.phone:
        return '+' + user.phone.lstrip('+')
    if user.username:
        return '@' + user.username.casefold()
    return f'telegram:{user.id}'


def fetch(now, days: int, limit: int):
    """Recent personal chats as chat dicts for sources.chat_threads, newest dialogs first."""
    creds = credentials()
    if not creds.get('session'):
        raise NotSignedIn('Telegram reader not signed in')
    since = now - timedelta(days=days)

    async def read():
        telegram = client(creds, creds['session'])
        await telegram.connect()
        try:
            if not await telegram.is_user_authorized():
                raise NotSignedIn('Telegram session ended; run setup again')
            chats = []
            async for dialog in telegram.iter_dialogs(limit=DIALOG_LIMIT):
                user = dialog.entity
                if (not dialog.is_user or not dialog.date or dialog.date < since or user.bot or user.is_self
                        or user.deleted or user.id in SERVICE_USERS):
                    continue
                messages = []
                async for message in telegram.iter_messages(user, limit=limit):
                    if message.date < since:
                        break
                    text = text_of(message)
                    if text is not None:
                        messages.append({'id': str(message.id), 'from_me': bool(message.out),
                                         'at': message.date.isoformat(), 'text': text})
                name = ' '.join(part for part in (user.first_name, user.last_name) if part)
                chats.append({'chat': str(user.id), 'address': address(user), 'name': name, 'messages': messages,
                              'automated': bool(getattr(user, 'support', False))})
            return chats
        finally:
            await telegram.disconnect()
    chats = in_thread(read)
    return chats, {'status': 'ok', 'chats': len(chats)}


def setup_window() -> None:
    """Sign in once. The user types the api_id/api_hash from my.telegram.org, the phone and the login code."""
    import tkinter as tk
    from tkinter import ttk
    from telethon.errors import SessionPasswordNeededError

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    state = {}

    def call(coroutine, timeout=90):
        return asyncio.run_coroutine_threadsafe(coroutine, loop).result(timeout=timeout)

    root = tk.Tk()
    root.title('Aurelius — Telegram chats (read-only)')
    frame = ttk.Frame(root, padding=16)
    frame.grid()
    ttk.Label(frame, wraplength=420, justify='left', text=(
        'Lets the attention scan read your one-to-one Telegram chats. It never sends or marks anything as read.\n'
        '1. Sign in at my.telegram.org → API development tools, create an app, and copy api_id and api_hash.\n'
        '2. Enter them with your phone number (international format) and press Send code.\n'
        '3. Type the code Telegram sends you, and your cloud password if you set one.')).grid(columnspan=2, sticky='w')
    fields = {}
    for row, (key, label, secret) in enumerate((('api_id', 'api_id', False), ('api_hash', 'api_hash', True),
                                                 ('phone', 'Phone', False), ('code', 'Login code', False),
                                                 ('password', 'Cloud password (if any)', True)), start=1):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=2)
        fields[key] = ttk.Entry(frame, width=36, show='•' if secret else '')
        fields[key].grid(row=row, column=1, pady=2)
    message = tk.StringVar(value='Signed in already; signing in again replaces the session.' if configured() else '')
    ttk.Label(frame, textvariable=message, wraplength=420, foreground='#555').grid(row=7, columnspan=2, sticky='w', pady=8)

    def value(key):
        return fields[key].get().strip()

    def send_code():
        try:
            creds = {'api_id': int(value('api_id')), 'api_hash': value('api_hash')}
            telegram = client(creds)
            call(telegram.connect())
            call(telegram.send_code_request(value('phone')))
            state.update(client=telegram, creds=creds)
            message.set('Code sent. Type it above and press Sign in.')
        except ValueError:
            message.set('api_id must be the number shown on my.telegram.org.')
        except Exception as error:
            message.set(f'Could not send the code ({type(error).__name__}). Check the values and try again.')

    def sign_in():
        telegram = state.get('client')
        if not telegram:
            message.set('Press Send code first.')
            return
        try:
            try:
                call(telegram.sign_in(phone=value('phone'), code=value('code')))
            except SessionPasswordNeededError:
                if not value('password'):
                    message.set('This account has a cloud password. Type it and press Sign in again.')
                    return
                call(telegram.sign_in(password=value('password')))
            me = call(telegram.get_me())
            accounts.secret_write(SECRET, {**state['creds'], 'session': telegram.session.save()})
            call(telegram.disconnect())
            state.clear()
            for entry in fields.values():
                entry.delete(0, 'end')
            for button in buttons.winfo_children():  # another attempt would only add another login to the account
                button.configure(state='disabled')
            message.set(f'Done: signed in as {me.first_name}. The next attention scan reads your chats. Close this window.')
        except Exception as error:
            message.set(f'Sign-in failed ({type(error).__name__}). Check the code and try again.')

    buttons = ttk.Frame(frame)
    buttons.grid(row=6, columnspan=2, pady=6)
    ttk.Button(buttons, text='Send code', command=send_code).grid(row=0, column=0, padx=4)
    ttk.Button(buttons, text='Sign in', command=sign_in).grid(row=0, column=1, padx=4)
    root.lift()
    root.attributes('-topmost', True)
    root.after(800, lambda: root.attributes('-topmost', False))
    root.mainloop()
    if state.get('client'):
        call(state['client'].disconnect(), timeout=10)


def forget() -> str:
    creds = credentials()
    if creds.get('session'):
        async def log_out():
            telegram = client(creds, creds['session'])
            await telegram.connect()
            await telegram.log_out()
        try:
            in_thread(log_out)
        except Exception:
            pass  # the local session is removed regardless; it can also be ended in Telegram > Devices
    path = accounts.token_path(SECRET)
    if path.exists():
        path.unlink()
    return 'Telegram reader signed out.'


def main(argv=None) -> int:
    command = (argv or sys.argv[1:] or ['status'])[0]
    if command == 'setup':
        setup_window()
    elif command == 'forget':
        print(forget())
    elif command == 'status':
        print('signed in' if configured() else 'not set up: python -m integrations.attention.telegram_user setup')
    else:
        print('usage: setup | status | forget')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
