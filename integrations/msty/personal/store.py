from pathlib import Path
import json
import re

ROOT = Path(r'G:\.codex-work\aurelius-private')
CONFIG = ROOT / 'accounts.json'


def defaults():
    return {'version': 1, 'accounts': [
        {'id': 'proton', 'label': 'Proton personal / sensitive', 'group': 'personal', 'kind': 'bridge', 'username': '', 'host': '127.0.0.1', 'port': 1143, 'tls': 'starttls', 'ca_file': '', 'sent_folder': '', 'enabled': False},
        {'id': 'gmail', 'label': 'Gmail personal', 'group': 'personal', 'kind': 'gmail', 'username': '', 'host': 'imap.gmail.com', 'port': 993, 'tls': 'ssl', 'sent_folder': '', 'enabled': False},
        {'id': 'icloud', 'label': 'Apple iCloud Mail', 'group': 'personal', 'kind': 'icloud', 'username': '', 'host': 'imap.mail.me.com', 'port': 993, 'tls': 'ssl', 'sent_folder': '', 'enabled': False},
        {'id': 'outlook-personal', 'label': 'Outlook personal', 'group': 'personal', 'kind': 'outlook', 'username': '', 'client_id': '', 'enabled': False},
        {'id': 'outlook-philanthropy', 'label': 'Secondary Outlook', 'group': 'philanthropy', 'kind': 'outlook', 'username': '', 'client_id': '', 'enabled': False},
        {'id': 'rotary', 'label': 'Secondary Google-hosted email', 'group': 'philanthropy', 'kind': 'gmail', 'username': '', 'host': 'imap.gmail.com', 'port': 993, 'tls': 'ssl', 'sent_folder': '', 'enabled': False},
        {'id': 'work', 'label': 'Work email', 'group': 'work', 'kind': 'imap', 'username': '', 'host': '', 'port': 993, 'tls': 'ssl', 'sent_folder': '', 'enabled': False},
        {'id': 'proton-calendar', 'label': 'Proton Calendar', 'group': 'personal', 'kind': 'calendar', 'path': '', 'enabled': False},
        {'id': 'proton-drive', 'label': 'Proton Drive local folder', 'group': 'personal', 'kind': 'drive', 'path': '', 'enabled': False},
    ]}


def load():
    config = json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else defaults()
    existing = {account['id'] for account in config['accounts']}
    config['accounts'].extend(account for account in defaults()['accounts'] if account['id'] not in existing)
    return config


def save(config):
    ROOT.mkdir(parents=True, exist_ok=True)
    temp = CONFIG.with_suffix('.tmp')
    temp.write_text(json.dumps(config, indent=2), encoding='utf-8')
    temp.replace(CONFIG)


def token_path(account_id):
    if not re.fullmatch(r'[a-z0-9-]{1,60}', account_id):
        raise ValueError('Invalid account id')
    return ROOT / (account_id + '.dpapi')


def secret_read(account_id):
    import win32crypt
    path = token_path(account_id)
    if not path.exists():
        return {}
    return json.loads(win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)[1])


def secret_write(account_id, value):
    import win32crypt
    ROOT.mkdir(parents=True, exist_ok=True)
    path = token_path(account_id)
    encrypted = win32crypt.CryptProtectData(json.dumps(value).encode(), 'Aurelius local account', None, None, None, 0)
    temp = path.with_suffix('.tmp')
    temp.write_bytes(encrypted)
    temp.replace(path)
