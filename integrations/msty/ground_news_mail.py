"""Read only Ground News mail using a Windows Credential Manager credential.

No SMTP, mailbox mutations, remote images, or tracking-link requests.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
import imaplib
import json
from pathlib import Path
import re
import ssl

HOST = 'imap.example.invalid'
PORT = 993
USERNAME = 'account@example.invalid'
CREDENTIAL = 'Aurelius/GroundNews/Dinahosting'
DOMAINS = ('ground.news', 'groundnews.co', 'groundnews.com', 'groundnews.app')
MAX_MESSAGE = 1_500_000
STATUS = Path(__file__).with_name('ground_news_setup_status.json')


def read_credential():
    import win32cred
    value = win32cred.CredRead(CREDENTIAL, win32cred.CRED_TYPE_GENERIC)
    return value['UserName'], value['CredentialBlob'].decode('utf-16-le')


def allowed_sender(message) -> bool:
    address = parseaddr(str(message.get('From', '')))[1].lower()
    domain = address.rpartition('@')[2]
    return domain in DOMAINS


def recent_date(message, now):
    try:
        date = parsedate_to_datetime(str(message.get('Date', '')))
        if date.tzinfo and now - timedelta(days=14) <= date <= now + timedelta(minutes=5):
            return date
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def fetch_newsletters(now=None, credential_reader=read_credential, imap_factory=imaplib.IMAP4_SSL):
    now = now or datetime.now(timezone.utc)
    username, password = credential_reader()
    newsletters = []
    with imap_factory(HOST, PORT, ssl_context=ssl.create_default_context(), timeout=20) as client:
        client.login(username, password)
        password = None
        status, _ = client.select('INBOX', readonly=True)
        if status != 'OK':
            raise RuntimeError('Inbox selection failed')
        since = (now - timedelta(days=14)).strftime('%d-%b-%Y')
        ids = set()
        for domain in DOMAINS:
            status, data = client.uid('search', None, 'SINCE', since, 'FROM', '"@' + domain + '"')
            if status != 'OK':
                raise RuntimeError('Newsletter search failed')
            ids.update(data[0].split() if data and data[0] else [])
        # Read headers before bodies, including a size limit and exact sender check.
        for uid in sorted(ids, key=int, reverse=True)[:30]:
            status, data = client.uid('fetch', uid, '(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
            if status != 'OK':
                continue
            part = next((part for part in data if isinstance(part, tuple)), None)
            if not part:
                continue
            size = re.search(rb'RFC822.SIZE\s+(\d+)', part[0])
            if not size or int(size[1]) > MAX_MESSAGE:
                continue
            header = BytesParser(policy=policy.default).parsebytes(part[1])
            date = recent_date(header, now)
            subject = str(header.get('Subject', ''))
            if not allowed_sender(header) or not date:
                continue
            if re.search(r'receipt|invoice|payment|renew|password|verification|sign.in|subscription', subject, re.I):
                continue
            status, data = client.uid('fetch', uid, '(BODY.PEEK[])')
            if status != 'OK':
                continue
            part = next((part for part in data if isinstance(part, tuple)), None)
            if not part or len(part[1]) > MAX_MESSAGE:
                continue
            message = BytesParser(policy=policy.default).parsebytes(part[1])
            if not allowed_sender(message):
                continue
            body = message.get_body(preferencelist=('html', 'plain'))
            if body is None:
                continue
            newsletters.append({'subject': subject, 'date': date.isoformat(),
                                'from': parseaddr(str(message.get('From', '')))[1],
                                'content_type': body.get_content_type(), 'body': body.get_content()})
    return newsletters


def setup():
    import tkinter as tk
    from tkinter import messagebox
    import win32cred
    root = tk.Tk()
    root.title('Aurelius — Ground News mailbox setup')
    root.geometry('560x300')
    tk.Label(root, text='Read Ground News newsletters via IMAP', font=('Segoe UI', 13)).pack(pady=12)
    tk.Label(root, text=HOST + ':993 (SSL/TLS)').pack()
    tk.Label(root, text='Mailbox username').pack(pady=(12, 0))
    user = tk.Entry(root, width=55)
    user.insert(0, USERNAME)
    user.pack()
    tk.Label(root, text='Mailbox password — saved in Windows Credential Manager').pack(pady=(12, 0))
    password = tk.Entry(root, show='*', width=55)
    password.pack()
    tk.Label(root, text='No password is sent to Codex or written to a configuration file.').pack(pady=8)

    def save():
        if not password.get() or not user.get().strip():
            return
        try:
            win32cred.CredWrite({'Type': win32cred.CRED_TYPE_GENERIC, 'TargetName': CREDENTIAL,
                                'UserName': user.get().strip(),
                                'CredentialBlob': password.get().encode('utf-16-le'),
                                'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE}, 0)
            password.delete(0, tk.END)
            STATUS.write_text(json.dumps({'credential_saved': True}), encoding='utf-8')
            root.destroy()
        except Exception:
            messagebox.showerror('Setup failed', 'Windows could not save the credential.')

    tk.Button(root, text='Save securely', command=save).pack(pady=5)
    password.focus_set()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    if args.setup:
        setup()
        return
    try:
        messages = fetch_newsletters()
        if args.preview:
            args.preview.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': 'ok', 'newsletters': len(messages),
                          'items': [{'subject': m['subject'], 'date': m['date']} for m in messages]}, ensure_ascii=True))
    except Exception as error:
        # Server exceptions may contain sensitive input; never print their text.
        print(json.dumps({'status': 'unavailable', 'error_type': type(error).__name__}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
