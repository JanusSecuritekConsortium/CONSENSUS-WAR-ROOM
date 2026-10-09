"""Setup readiness is distinct from a successful read-only connection test."""
from pathlib import Path
from . import store


def missing_fields(account):
    kind = account['kind']
    required = {
        'imap': ('username', 'host', 'port', 'tls'),
        'gmail': ('username', 'host', 'port', 'tls'),
        'icloud': ('username', 'host', 'port', 'tls'),
        'bridge': ('username', 'host', 'port', 'tls', 'ca_file'),
        'outlook': ('username', 'client_id'), 'drive': ('path',), 'calendar': (),
    }.get(kind, ())
    missing = [key.replace('_', ' ') for key in required if not str(account.get(key, '')).strip()]
    # Inspect existence only. Never decrypt credentials just to draw the UI.
    if kind not in ('drive', 'calendar') and not store.token_path(account['id']).is_file():
        missing.append('Microsoft sign-in' if kind == 'outlook' else 'saved password')
    if kind == 'calendar' and not account.get('path') and not store.token_path(account['id']).is_file():
        missing.append('calendar file or saved HTTPS link')
    if account.get('path') and not Path(account['path']).exists():
        missing.append('existing local path')
    if kind == 'bridge' and account.get('ca_file') and not Path(account['ca_file']).is_file():
        missing.append('existing certificate file')
    return missing


def connection_state(account):
    if missing_fields(account):
        return 'Setup incomplete'
    if not account.get('last_test_at'):
        return 'Not tested'
    if not account.get('last_test_ok'):
        return 'Test failed'
    if account.get('last_test_warnings'):
        return 'Test passed (limited)'
    return '✓ Test passed'


def account_status(account):
    parts = [connection_state(account), 'Reviews on' if account.get('enabled') else 'Reviews off']
    missing = missing_fields(account)
    if missing:
        parts.append('Missing: ' + ', '.join(missing))
    if account.get('last_test_at'):
        parts.append('Last test: ' + account['last_test_at'])
    parts.extend(account.get('last_test_warnings', []))
    return ' · '.join(parts)


def account_label(account):
    return connection_state(account) + ' — ' + account['label']
