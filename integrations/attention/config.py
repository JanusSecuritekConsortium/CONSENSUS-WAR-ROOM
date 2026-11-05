"""Settings for the Personal Attention Manager. Secrets never live here."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from core.paths import on_portable_drive

# The shared state folder is plain files plus the SQLite file that is authoritative for them.
DEFAULT_HOME = on_portable_drive('Obsidian', 'Personal Attention')

DEFAULTS = {
    'owner_name': 'the user',       # how the classifier refers to the mailbox owner
    'model': 'qwen3.5:9b',
    'msty_base_url': 'http://127.0.0.1:11964',
    'model_timeout_seconds': 300,
    'timezone': 'Europe/Madrid',
    'lookback_days': 60,             # only conversations active in this window are scanned
    'quiet_after_days': 30,          # older conversations are still tracked, but never brief or alert
    'messages_per_folder': 60,
    'max_threads_per_scan': 40,      # model calls per scan; the rest wait for the next scan
    'context_messages': 6,           # newest messages sent to the model per changed conversation
    'high_confidence': 0.85,
    'medium_confidence': 0.60,
    'reply_high_after_hours': 24,
    'reply_overdue_after_hours': 72,
    'waiting_remind_after_days': 5,
    'important_contacts': [],        # contact ids that rank one level higher
    'retain_completed_days': 30,
    'brief_times': ['08:00'],        # one brief a day; only very important items alert in between
    'alert_now': True,               # urgent items, or high ones from favourites, alert at the next scan
    'auto_drafts': True,             # draft replies in the owner's own style; drafts are never sent
    'style_examples': 5,             # the owner's own sent messages shown to the model per draft
    'google_contacts_csv': '',       # empty means <state folder>/system/google-contacts.csv
    'scan_every_minutes': 30,
    'mail_accounts': [],             # empty means every enabled mail account in the local connector settings
    'telegram_chats': True,          # read personal Telegram chats once signed in (telegram_user setup)
    'whatsapp_chats': True,          # read personal WhatsApp chats once linked (whatsapp pair)
    'chat_context_messages': 15,     # chat messages are short, so the model sees more of them
    'organise_mail': False,          # sort inbox email into folders after each scan (organise.py)
    'organise_accounts': [],         # empty means every enabled IMAP account
    'organise_per_run': 40,          # inbox emails looked at per run, newest first; the rest wait
    'organise_questions_per_run': 5, # Telegram questions sent per run when unsure
    'organise_new_folder_min': 3,    # emails in one run that must clearly need a folder before it is created
    'memory_review': False,          # ask on Telegram about Msty Go memory suggestions after each scan (memory_review.py)
    'memory_review_per_run': 5,
}


def home() -> Path:
    return Path(os.environ.get('PERSONAL_ATTENTION_HOME') or DEFAULT_HOME)


def settings_path() -> Path:
    return home() / 'system' / 'settings.json'


def load() -> dict:
    settings = dict(DEFAULTS)
    try:
        stored = json.loads(settings_path().read_text(encoding='utf-8'))
        settings.update({key: value for key, value in stored.items() if key in DEFAULTS})
    except (OSError, ValueError):
        pass
    url = os.environ.get('ATTENTION_MSTY_BASE_URL') or os.environ.get('MSTY_BASE_URL')
    if url:
        settings['msty_base_url'] = url
    settings['msty_base_url'] = loopback(settings['msty_base_url'])
    settings['tz'] = ZoneInfo(settings['timezone'])
    return settings


def loopback(url: str) -> str:
    """Conversation text may only go to a model on this PC."""
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or parts.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('The attention classifier must use a local Msty endpoint')
    return url.rstrip('/').removesuffix('/v1')


def save_defaults() -> None:
    """Write the editable settings file once so the user can see every option."""
    path = settings_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULTS, indent=2) + '\n', encoding='utf-8')
