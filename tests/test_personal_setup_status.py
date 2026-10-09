from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import json
import pytest
from integrations.msty.personal import store, connectors, status, audit


def profile(account_id):
    return next(a for a in store.defaults()['accounts'] if a['id'] == account_id)


def test_saved_empty_outlook_is_not_connected(tmp_path):
    account = dict(profile('outlook-personal'), setup_saved=True, enabled=True,
                   last_test_at='2026-09-27', last_test_ok=True)
    with patch.object(store, 'ROOT', tmp_path):
        assert status.connection_state(account) == 'Setup incomplete'
        assert 'client id' in status.account_status(account)
        assert '✓' not in status.account_label(account)


def test_credentials_and_save_do_not_prove_connection(tmp_path):
    (tmp_path / 'rotary.dpapi').touch()
    account = dict(profile('rotary'), username='test@example.org', setup_saved=True)
    with patch.object(store, 'ROOT', tmp_path), patch.object(store, 'secret_read', side_effect=AssertionError('UI must not decrypt')):
        assert status.connection_state(account) == 'Not tested'
        account.update(last_test_at='2026-09-27', last_test_ok=False)
        assert status.connection_state(account) == 'Test failed'
        account['last_test_ok'] = True
        assert status.connection_state(account) == '✓ Test passed'
        account['last_test_warnings'] = ['Sent folder unavailable']
        assert status.connection_state(account) == 'Test passed (limited)'


def test_load_adds_icloud_preserving_existing_accounts(tmp_path):
    config_path = tmp_path / 'accounts.json'
    existing = dict(profile('work'), username='test@example.org', enabled=True)
    config_path.write_text(json.dumps({'version': 1, 'accounts': [existing]}))
    with patch.object(store, 'CONFIG', config_path), patch.object(store, 'ROOT', tmp_path):
        loaded = store.load()
        assert loaded['accounts'][0] == existing
        apple = next(a for a in loaded['accounts'] if a['id'] == 'icloud')
        assert (apple['host'], apple['port'], apple['tls']) == ('imap.mail.me.com', 993, 'ssl')
        assert not apple['enabled']
        assert connectors.READERS[apple['kind']] is connectors.imap_mail
        store.save(loaded)
        assert len(store.load()['accounts']) == 9


def test_unreadable_folders_are_not_a_success():
    client = MagicMock()
    client.__enter__.return_value = client
    client.list.return_value = ('OK', [])
    client.select.return_value = ('NO', [])
    with patch.object(connectors, 'secret_read', return_value={'password': 'test-only'}), patch.object(connectors.imaplib, 'IMAP4_SSL', return_value=client):
        with pytest.raises(RuntimeError, match='No readable mail folders'):
            connectors.imap_mail(profile('work'), datetime.now(timezone.utc))


def test_empty_drive_path_does_not_inventory_working_directory():
    with pytest.raises(ValueError, match='Select a local Proton Drive folder'):
        connectors.drive_files(profile('proton-drive'), datetime.now(timezone.utc))


def test_audit_reports_counts_without_private_content():
    result = {'id': 'gmail', 'status': 'ok', 'messages': [{'body': 'PRIVATE', 'subject': 'PRIVATE'}],
              'events': [{'title': 'PRIVATE'}], 'files': [{'name': 'PRIVATE'}]}
    with patch.object(audit, 'missing_fields', return_value=[]), patch.object(audit, 'collect', return_value=[result]):
        summary = audit.check(profile('gmail'))
    assert summary['counts'] == {'messages': 1, 'events': 1, 'files': 1}
    assert 'PRIVATE' not in json.dumps(summary)
