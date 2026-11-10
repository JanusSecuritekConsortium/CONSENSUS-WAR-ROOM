"""Email folder sorting with a fake mailbox and model. No mail server, Msty or Telegram is touched."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.attention import config, organise, store, tools

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
ACCOUNT = {'id': 'work', 'kind': 'imap', 'enabled': True}


class FakeBox:
    """Folders map raw name to a list of messages; uids are positions + 1 in the original listing."""

    def __init__(self, folders, can_move=True):
        self.data = folders
        self.validity = '7'
        self.can_move = can_move
        self.created = []
        self.closed = False

    def folders(self):
        flags = {'INBOX': set(), 'Sent': {'\\sent'}, 'Trash': {'\\trash'}}
        return [{'raw': raw, 'name': organise.utf7_decode(raw), 'delimiter': '/', 'flags': flags.get(raw, set())}
                for raw in self.data]

    def uids(self, raw):
        return [str(m['uid']).encode() for m in self.data[raw]]

    def _get(self, raw, uid):
        return next(m for m in self.data[raw] if str(m['uid']).encode() == uid)

    def headers(self, raw, uid, fields='FROM LIST-ID'):
        m = self._get(raw, uid)
        return {'from': m['from'], 'subject': m.get('subject', ''), 'list-id': m.get('list', ''),
                'message-id': m['id'], 'references': m.get('refs', ''), 'in-reply-to': '', 'flagged': m.get('flagged', False)}

    def snippet(self, raw, uid):
        return self._get(raw, uid).get('body', '')

    def find(self, raw, message_id):
        found = [m for m in self.data[raw] if m['id'] == message_id]
        return str(found[0]['uid']).encode() if found else None

    def move(self, source, uid, target):
        if not self.can_move:
            raise RuntimeError('This mail server cannot move messages')
        message = self._get(source, uid)
        self.data[source].remove(message)
        self.data[target].append(message)
        return True

    def create(self, raw):
        self.created.append(raw)
        self.data[raw] = []

    def close(self):
        self.closed = True


def mail(uid, sender, subject='Hello', **extra):
    return {'uid': uid, 'from': f'Someone <{sender}>', 'subject': subject, 'id': f'<m{uid}@example.test>', **extra}


def model(answers):
    """A fake Msty endpoint answering by subject."""
    calls = []

    def post(url, json=None, timeout=None):
        content = json['messages'][1]['content']
        subject = content.split('Subject: ', 1)[1].split('\n', 1)[0]
        calls.append(subject)

        class Response:
            def raise_for_status(self):
                pass

            def json(self_inner):
                return {'message': {'content': __import__('json').dumps(answers[subject])}}
        return Response()
    post.calls = calls
    return post


def answer(folder=None, new=None, confidence=0.95, alternatives=()):
    return {'folder': folder, 'new_folder': new, 'alternatives': list(alternatives), 'confidence': confidence, 'reason': 'test'}


class OrganiseTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        patcher = patch.dict(os.environ, {'PERSONAL_ATTENTION_HOME': str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = dict(config.load(), organise_mail=True)
        accounts = patch.object(organise, 'accounts', lambda settings: [ACCOUNT])
        accounts.start()
        self.addCleanup(accounts.stop)
        self.sent = []

    def notify(self, db, limit, now):
        rows = db.execute('SELECT id FROM questions WHERE asked_at IS NULL LIMIT ?', (limit,)).fetchall()
        for row in rows:
            db.execute('UPDATE questions SET asked_at=? WHERE id=?', (now.isoformat(), row['id']))
            self.sent.append(row['id'])
        return len(rows)

    def run_once(self, box, post):
        return organise.run(settings=self.settings, now=NOW, opener=lambda account: box, notify=self.notify, post=post)

    def test_an_expired_sorter_cannot_renew_or_release_a_newer_claim(self):
        with organise.connect(self.home) as first, organise.connect(self.home) as second:
            old = organise.claim(first, NOW)
            renewed_at = NOW + timedelta(minutes=20)
            self.assertTrue(organise.renew(first, old, renewed_at))
            self.assertIsNone(organise.claim(second, NOW + timedelta(minutes=31)))
            later = NOW + timedelta(minutes=51)
            new = organise.claim(second, later)
            self.assertNotEqual(old, new)
            self.assertFalse(organise.renew(first, old, later))
            organise.release(first, old)
            self.assertIsNone(organise.claim(first, later))
            organise.release(second, new)
            self.assertIsNotNone(organise.claim(first, later))

    def test_learned_sender_moves_without_the_model(self):
        box = FakeBox({'INBOX': [mail(10, 'bills@power.test', 'Your bill')], 'Sent': [], 'Trash': [],
                       'Invoices': [mail(1, 'bills@power.test'), mail(2, 'bills@power.test')]})
        post = model({})
        result = self.run_once(box, post)
        self.assertEqual(result['accounts']['work']['moved'], 1)
        self.assertEqual(post.calls, [])
        self.assertEqual(box.data['INBOX'], [])

    def test_sure_model_moves_and_doubt_asks(self):
        box = FakeBox({'INBOX': [mail(10, 'a@shop.test', 'Order shipped'), mail(11, 'b@x.test', 'Maybe')],
                       'Shopping': [], 'Travel': []})
        post = model({'Order shipped': answer('Shopping'), 'Maybe': answer('Travel', confidence=0.6, alternatives=['Shopping'])})
        result = self.run_once(box, post)
        self.assertEqual(result['accounts']['work']['moved'], 1)
        self.assertEqual(result['accounts']['work']['asked'], 1)
        self.assertEqual([m['subject'] for m in box.data['Shopping']], ['Order shipped'])
        questions = organise.pending(limit=5)
        self.assertEqual([o['label'] for o in questions[0]['options']], ['Travel', 'Shopping'])
        self.assertEqual(self.sent, [questions[0]['id']])

    def test_folder_patterns_reach_the_model(self):
        box = FakeBox({'INBOX': [mail(10, 'new@club.test', 'Match on Sunday')],
                       'Sport': [mail(1, 'coach@club.test', 'Training moved'), mail(2, 'ref@league.test', 'Fixtures')]})
        prompts = []
        post = model({'Match on Sunday': answer('Sport')})

        def spy(url, json=None, timeout=None):
            prompts.append(json['messages'][0]['content'])
            return post(url, json=json, timeout=timeout)
        self.run_once(box, spy)
        self.assertIn('- Sport: usually from club.test, league.test; recent subjects: Training moved | Fixtures', prompts[0])
        self.assertEqual(len(box.data['Sport']), 3)

    def test_answer_moves_and_teaches_the_sender(self):
        box = FakeBox({'INBOX': [mail(11, 'b@x.test', 'Maybe')], 'Travel': []})
        self.run_once(box, model({'Maybe': answer('Travel', confidence=0.5)}))
        question = organise.pending()[0]
        text = organise.file(question['id'], choice=0, opener=lambda a: box, now=NOW, settings=self.settings)
        self.assertIn('Moved to Travel', text)
        self.assertEqual(len(box.data['Travel']), 1)
        self.assertIn('Already answered', organise.file(question['id'], choice=0, opener=lambda a: box, settings=self.settings))
        box.data['INBOX'].append(mail(12, 'b@x.test', 'Again'))
        post = model({})
        self.assertEqual(self.run_once(box, post)['accounts']['work']['moved'], 1)
        self.assertEqual(post.calls, [])

    def test_new_folder_needs_enough_emails(self):
        inbox = [mail(i, f'n{i}@club.test', f'Club {i}') for i in range(1, 5)] + [mail(9, 'z@solo.test', 'Solo')]
        box = FakeBox({'INBOX': inbox, 'Work': []})
        answers = {f'Club {i}': answer(new='Club') for i in range(1, 5)}
        answers['Solo'] = answer(new='Solo things')
        result = self.run_once(box, model(answers))
        self.assertEqual(box.created, ['Club'])
        self.assertEqual(len(box.data['Club']), 4)
        self.assertEqual(result['accounts']['work']['asked'], 1)
        self.assertEqual(organise.pending()[0]['options'][0]['label'], 'New: Solo things')

    def test_open_attention_items_and_flagged_mail_stay(self):
        box = FakeBox({'INBOX': [mail(10, 'p@friend.test', 'Question'), mail(11, 'q@x.test', 'Flag', flagged=True)],
                       'Friends': []})
        key = organise.thread_key('work', {'message-id': '<m10@example.test>'}, '7:10')
        with store.connect() as db:
            db.execute("INSERT INTO items(id,key,kind,state,confidence,channel,thread_key,title,summary,origin,"
                       "created_at,updated_at,first_seen_at) "
                       "VALUES('reply-1','k','reply','NEEDS_REPLY',0.9,'email',?,'t','s','scan',?,?,?)",
                       (key, NOW.isoformat(), NOW.isoformat(), NOW.isoformat()))
        post = model({})
        result = self.run_once(box, post)
        self.assertEqual(result['accounts']['work']['held'], 2)
        self.assertEqual(len(box.data['INBOX']), 2)
        self.assertEqual(post.calls, [])

    def test_keep_when_sure_and_nothing_twice(self):
        box = FakeBox({'INBOX': [mail(10, 'mum@home.test', 'Dinner?')], 'Bills': []})
        post = model({'Dinner?': answer()})
        self.assertEqual(self.run_once(box, post)['accounts']['work']['kept'], 1)
        self.run_once(box, post)
        self.assertEqual(post.calls, ['Dinner?'])

    def test_undo_moves_back(self):
        box = FakeBox({'INBOX': [mail(10, 'a@shop.test', 'Order')], 'Shopping': []})
        self.run_once(box, model({'Order': answer('Shopping')}))
        move = organise.status()['recent_moves'][0]
        self.assertEqual(move['target'], 'Shopping')
        self.assertIn('Moved back', organise.undo(move['id'], opener=lambda a: box, settings=self.settings))
        self.assertEqual(len(box.data['INBOX']), 1)
        self.assertIn('Nothing to undo', organise.undo(move['id'], opener=lambda a: box, settings=self.settings))

    def test_off_by_default_and_system_folders_are_never_targets(self):
        self.assertFalse(config.DEFAULTS['organise_mail'])
        self.assertEqual(organise.run(settings=dict(self.settings, organise_mail=False)), {'status': 'off'})
        box = FakeBox({'INBOX': [], 'Sent': [], 'Trash': [], 'Spam': [], 'Folders/Bank': [], 'Labels/Red': []})
        names = [f['name'] for f in organise.candidates({'kind': 'bridge'}, box.folders())]
        self.assertEqual(names, ['Folders/Bank'])

    def test_folder_names_round_trip_modified_utf7(self):
        for name in ('Facturación', 'R&D', 'Viajes 2026', 'Ключи'):
            self.assertEqual(organise.utf7_decode(organise.utf7_encode(name)), name)
        self.assertEqual(organise.utf7_encode('Facturación'), 'Facturaci&APM-n')

    def test_tools_are_on_the_msty_connection(self):
        names = {tool['name'] for tool in tools.TOOLS}
        for name in ('mail_folders_status', 'mail_folders_questions', 'mail_folders_file', 'mail_folders_undo'):
            self.assertIn(name, tools.COMPACT)
            self.assertIn(name, names)
            self.assertIn(name, tools.HANDLERS)


if __name__ == '__main__':
    unittest.main()
