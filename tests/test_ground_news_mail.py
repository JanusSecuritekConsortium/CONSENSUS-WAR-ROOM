from datetime import datetime, timezone
from email.message import EmailMessage
from unittest.mock import MagicMock

from integrations.msty.ground_news_mail import fetch_newsletters, allowed_sender


def test_exact_sender_domain():
    for sender, expected in [('Ground News <news@ground.news>', True),
                             ('fake@ground.news.evil.test', False),
                             ('Ground News <other@example.com>', False)]:
        message = EmailMessage()
        message['From'] = sender
        assert allowed_sender(message) == expected


def test_read_only_and_filtered_body_fetch():
    message = EmailMessage()
    message['From'] = 'news@groundnews.co'
    message['Subject'] = 'Daily Ground'
    message['Date'] = 'Wed, 16 Sep 2026 05:00:00 +0000'
    message.set_content('Newsletter text')
    raw = message.as_bytes()
    fake = MagicMock()
    client = fake.return_value.__enter__.return_value
    client.select.return_value = ('OK', [b'2'])

    def command(action, *args):
        if action == 'search':
            return 'OK', [b'1 2']
        uid, query = args
        if 'HEADER.FIELDS' in query:
            content = raw if uid == b'1' else raw.replace(b'news@groundnews.co', b'fake@evil.test')
            return 'OK', [(b'RFC822.SIZE 1000', content)]
        assert uid == b'1', 'Unrelated email body must not be read'
        assert query == '(BODY.PEEK[])'
        return 'OK', [(b'BODY[]', raw)]

    client.uid.side_effect = command
    result = fetch_newsletters(datetime(2026, 9, 16, 10, tzinfo=timezone.utc),
                               credential_reader=lambda: ('user', 'password'), imap_factory=fake)
    assert len(result) == 1
    assert result[0]['subject'] == 'Daily Ground'
    client.select.assert_called_once_with('INBOX', readonly=True)
    assert all(call.args[0] in ('search', 'fetch') for call in client.uid.call_args_list)
