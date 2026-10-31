"""Offline tests for the Personal Attention Manager: fake sources and model, temporary state folder."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.attention import api, classify, config, export, scan, sources, store, tools

NOW = datetime(2026, 10, 29, 16, 0, tzinfo=timezone.utc)


def message(mid, direction, at, text, sender='Laura <laura@example.com>', refs='', subject='Saturday', bulk=False):
    other = 'me@example.com'
    return {'id': mid, 'message_id': f'<{mid}@example.com>', 'references': refs, 'subject': subject,
            'from': sender if direction == 'inbox' else other, 'to': other if direction == 'inbox' else sender,
            'date': at.isoformat(), 'direction': direction, 'body': text, 'bulk': bulk}


def result(**overrides):
    base = {'waiting_on': 'none', 'needs_reply': False, 'reply_kind': 'none', 'informational': False, 'urgent': False,
            'confidence': 0.95, 'summary': 'Nothing to do.', 'action': None, 'commitments': [], 'appointment': None}
    base.update(overrides)
    return classify.validate(base)


class AttentionTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        patcher = patch.dict(os.environ, {'PERSONAL_ATTENTION_HOME': str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = config.load()
        self.mail = []
        self.answers = []
        self.classified = []
        self.drafted = []
        self.alerts = []

    def reader(self, now):
        threads = sources.mail_threads('gmail', self.mail, now, 7)
        return threads, {'email:gmail': {'status': 'ok', 'threads': len(threads)}}

    def classifier(self, thread):
        self.classified.append(thread['key'])
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return classify.validate(answer) if isinstance(answer, (str, dict)) else answer

    def drafter(self, item, name, settings, conversation=None, examples=None):
        self.drafted.append({'item': item['id'], 'examples': examples, 'conversation': conversation})
        return 'Hola! Sí, el sábado me va bien.\nAlex'

    def notify(self, title, text):
        self.alerts.append(text)

    def scan(self, now=NOW):
        return scan.run(now, settings=self.settings, readers={'email': self.reader}, classifier=self.classifier,
                        availability=lambda event, now: {'status': 'free', 'detail': 'That time appears free'},
                        drafter=self.drafter, notify=self.notify)

    def items(self, **filters):
        with store.connect() as db:
            return store.query_items(db, **filters)

    # 1, 7 and 2 ------------------------------------------------------------
    def test_direct_question_needs_reply(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=5), 'Are you free Saturday evening?')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question',
                               summary='Laura asked whether you are free Saturday evening.', action='Reply about Saturday')]
        self.scan()
        [item] = self.items()
        self.assertEqual((item['kind'], item['state'], item['contact_id']), ('reply', store.NEEDS_REPLY, 'laura'))
        self.assertTrue((self.home / 'attention' / 'open' / f'{item["id"]}.md').exists())

    def test_emoji_acknowledgement_and_informational_mail_create_nothing(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=2), '👍'),
                     message('m2', 'inbox', NOW - timedelta(hours=1), 'FYI the venue changed.', sender='Marta <marta@example.com>',
                             subject='Venue')]
        self.answers = [result(informational=True), result(summary='Thumbs up.')]
        self.scan()
        self.assertEqual(self.items(), [])
        with store.connect() as db:
            self.assertEqual({r['state'] for r in db.execute('SELECT state FROM threads')}, {store.NO_ACTION})

    def test_newsletter_is_never_sent_to_the_model(self):
        self.mail = [message('m1', 'inbox', NOW, 'Weekly deals', sender='Shop <noreply@shop.example>', bulk=True)]
        self.scan()
        self.assertEqual(self.classified, [])
        self.assertEqual(self.items(), [])

    # 3, 12 -----------------------------------------------------------------
    def test_owner_promise_creates_commitment_and_kept_promise_does_not(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(days=1, hours=2), 'Can you send me the PDF?', sender='Paul <paul@example.com>'),
                     message('m2', 'sent', NOW - timedelta(days=1), "I'll send it tomorrow.", sender='Paul <paul@example.com>',
                             refs='<m1@example.com>')]
        promise = {'text': 'Send Paul the PDF', 'due_date': '2026-10-29', 'due_text': 'tomorrow', 'completed': False, 'confidence': 0.97}
        self.answers = [result(waiting_on='owner', commitments=[promise], summary='You told Paul you would send the PDF.')]
        self.scan()
        [item] = self.items(kinds=['commitment'])
        self.assertEqual((item['state'], item['due_at']), (store.COMMITMENT_OPEN, '2026-10-29'))
        page = (self.home / 'commitments' / 'open' / f'{item["id"]}.md').read_text(encoding='utf-8')
        self.assertIn('status: open', page)

        self.mail.append(message('m3', 'sent', NOW - timedelta(hours=1), 'Here is the PDF.', sender='Paul <paul@example.com>',
                                 refs='<m1@example.com> <m2@example.com>'))
        self.answers = [result(waiting_on='contact', commitments=[dict(promise, completed=True)])]
        self.scan()
        self.assertEqual(self.items(kinds=['commitment']), [])
        with store.connect() as db:
            self.assertEqual(store.get_item(db, item['id'])['resolution'], 'detected_done')
        # A later reclassification that again reports the kept promise never reopens it.
        self.mail.append(message('m4', 'inbox', NOW, 'Thanks!', sender='Paul <paul@example.com>', refs='<m1@example.com>'))
        self.answers = [result(commitments=[dict(promise, completed=True)])]
        self.scan()
        self.assertEqual(self.items(kinds=['commitment']), [])

    def test_ambiguous_timing_is_kept_without_inventing_a_date(self):
        self.mail = [message('m1', 'sent', NOW - timedelta(hours=1), "I'll get back to you next week.", sender='Ana <ana@example.com>')]
        self.answers = [result(waiting_on='none', commitments=[{'text': 'Get back to Ana', 'due_date': 'next week',
                                                                'due_text': 'next week', 'completed': False, 'confidence': 0.9}])]
        self.scan()
        [item] = self.items()
        self.assertIsNone(item['due_at'])
        self.assertEqual(item['due_text'], 'next week')

    # 4, 5 ------------------------------------------------------------------
    def test_reply_moves_to_waiting_and_their_answer_returns_it_to_me(self):
        first = message('m1', 'inbox', NOW - timedelta(hours=6), 'Can you review the documents?')
        self.mail = [first]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='request', summary='Laura asked for a review.')]
        self.scan()
        [reply] = self.items()
        self.assertEqual(reply['state'], store.WAITING_ON_ME)

        self.mail.append(message('m2', 'sent', NOW - timedelta(hours=3), "Done. Let me know once you've reviewed them.",
                                 refs='<m1@example.com>'))
        self.answers = [result(waiting_on='contact', summary='You sent the documents; Laura is reviewing them.')]
        self.scan()
        [waiting] = self.items()
        self.assertEqual((waiting['kind'], waiting['state'], waiting['priority']), ('waiting', store.WAITING_ON_OTHER, 'LOW'))
        with store.connect() as db:
            self.assertEqual(store.get_item(db, reply['id'])['resolution'], 'replied')

        self.mail.append(message('m3', 'inbox', NOW - timedelta(hours=1), 'One question: can you sign page 3?',
                                 refs='<m1@example.com> <m2@example.com>'))
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='request', summary='Laura asked you to sign page 3.')]
        self.scan()
        [again] = self.items()
        self.assertEqual((again['kind'], again['state']), ('reply', store.WAITING_ON_ME))
        with store.connect() as db:
            self.assertEqual(store.get_item(db, waiting['id'])['resolution'], 'answered')

    # 6 ---------------------------------------------------------------------
    def test_meeting_proposal_becomes_appointment_candidate_with_availability(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=1), 'Dinner Saturday at 20:00?')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Laura proposed dinner.',
                               appointment={'title': 'Dinner with Laura', 'date': '2026-10-31', 'time': '20:00',
                                            'status': 'proposed', 'confidence': 0.9})]
        self.scan()
        [appointment] = self.items(kinds=['appointment'])
        self.assertEqual(appointment['state'], store.APPOINTMENT_PROPOSED)
        self.assertEqual(appointment['event']['availability'], 'free')
        self.assertEqual(len(self.items(kinds=['reply'])), 1)  # the question still needs a reply
        self.assertIn('appears free', api.current_brief()['brief'])

    # 8, 9 ------------------------------------------------------------------
    def test_duplicate_messages_and_rescans_do_not_duplicate_items(self):
        question = message('m1', 'inbox', NOW - timedelta(hours=2), 'Are you coming?')
        self.mail = [question, dict(question, direction='inbox'), dict(question, id='copy-in-other-folder')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Laura asked if you are coming.')]
        self.scan()
        self.scan()  # unchanged conversation: no model call, no new item
        self.assertEqual(len(self.classified), 1)
        self.assertEqual(len(self.items()), 1)

    def test_state_survives_restart_and_resolved_items_stay_resolved(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=2), 'Please confirm attendance.')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Confirm attendance.')]
        self.scan()
        [item] = self.items()
        api.mark_done(item['id'])
        # A new process sees the same file; even a forced reclassification keeps the item closed.
        with store.connect() as db:
            db.execute('UPDATE threads SET processed_fingerprint=NULL')
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Confirm attendance.')]
        self.scan()
        self.assertEqual(self.items(), [])
        with store.connect() as db:
            self.assertEqual(store.get_item(db, item['id'])['state'], store.COMPLETED)
        self.assertTrue((self.home / 'attention' / 'completed' / f'{item["id"]}.md').exists())

    # 10, 11 ----------------------------------------------------------------
    def test_msty_unavailable_leaves_state_untouched_and_retries_later(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=2), 'Are you free?')]
        self.answers = [classify.ModelUnavailable('ConnectionError')]
        summary = self.scan()
        self.assertEqual((summary['msty'], summary['pending'], self.items()), ('unavailable', 1, []))
        self.assertIn('Msty unavailable', api.current_brief()['brief'])
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Laura asked if you are free.')]
        self.scan()
        self.assertEqual(len(self.items()), 1)

    def test_invalid_model_json_is_rejected_without_corrupting_state(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=2), 'Are you free?')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Laura asked if you are free.')]
        self.scan()
        before = self.items()
        self.mail.append(message('m2', 'inbox', NOW - timedelta(hours=1), 'Hello?', refs='<m1@example.com>'))
        for bad in ('not json', '{"waiting_on": "maybe"}', {'waiting_on': 'owner', 'needs_reply': 'yes'},
                    {'waiting_on': 'owner', 'needs_reply': True, 'confidence': 7, 'summary': 'x'}):
            with self.subTest(bad=bad), self.assertRaises(classify.ModelOutputError):
                classify.validate(bad)
        self.answers = ['{"summary": "broken"']
        summary = self.scan()
        self.assertEqual(summary['errors'], 1)
        self.assertEqual([i['id'] for i in self.items()], [i['id'] for i in before])
        self.assertEqual(self.items()[0]['summary'], before[0]['summary'])

    # 13 --------------------------------------------------------------------
    def test_one_conversation_can_hold_several_actions(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=3), 'Can you send the slides and join a call Friday at 10:00?'),
                     message('m2', 'sent', NOW - timedelta(hours=2), "I'll send the slides tonight; let me check Friday.",
                             refs='<m1@example.com>')]
        self.answers = [result(waiting_on='owner', summary='Laura wants the slides and a Friday call.',
                               commitments=[{'text': 'Send Laura the slides', 'due_date': '2026-10-29', 'due_text': 'tonight',
                                             'completed': False, 'confidence': 0.95},
                                            {'text': 'Check Friday availability for Laura', 'due_date': None, 'due_text': None,
                                             'completed': False, 'confidence': 0.9}],
                               appointment={'title': 'Call with Laura', 'date': '2026-10-30', 'time': '10:00',
                                            'status': 'proposed', 'confidence': 0.9})]
        self.scan()
        kinds = sorted(i['kind'] for i in self.items())
        self.assertEqual(kinds, ['appointment', 'commitment', 'commitment'])

    # 14 --------------------------------------------------------------------
    def test_snoozed_item_stays_hidden_until_due(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=2), 'What do you think?')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Laura wants your view.')]
        self.scan()
        [item] = self.items()
        with store.connect() as db:
            store.transition(db, item['id'], 'snooze', NOW, until=NOW + timedelta(days=1))
            scan.refresh(db, NOW + timedelta(hours=23), self.settings)
            self.assertEqual(store.get_item(db, item['id'])['state'], store.SNOOZED)
            with self.assertRaises(store.InvalidTransition):
                store.transition(db, item['id'], 'snooze', NOW, until=NOW - timedelta(hours=1))
            scan.refresh(db, NOW + timedelta(days=1, minutes=1), self.settings)
            self.assertEqual(store.get_item(db, item['id'])['state'], store.NEEDS_REPLY)

    # 15 --------------------------------------------------------------------
    def test_old_unanswered_question_escalates(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=5), 'Can we talk?')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', summary='Laura wants to talk.')]
        self.scan()
        with store.connect() as db:
            levels = []
            for hours in (0, 20, 70):
                scan.refresh(db, NOW + timedelta(hours=hours), self.settings)
                item = store.query_items(db)[0]
                levels.append((item['priority'], item['overdue']))
        self.assertEqual(levels, [('NORMAL', False), ('HIGH', False), ('HIGH', True)])

    def test_medium_confidence_is_a_review_candidate_and_low_is_not_tracked(self):
        self.mail = [message('m1', 'inbox', NOW - timedelta(hours=2), 'maybe sometime?'),
                     message('m2', 'inbox', NOW - timedelta(hours=1), 'hm', sender='Marta <marta@example.com>', subject='x')]
        self.answers = [result(waiting_on='owner', needs_reply=True, reply_kind='question', confidence=0.4, summary='Unclear.'),
                        result(waiting_on='owner', needs_reply=True, reply_kind='question', confidence=0.7, summary='Maybe a question.')]
        self.scan()
        [item] = self.items()
        self.assertTrue(item['review'])
        self.assertEqual(item['priority'], 'LOW')
        self.assertIn('TO CONFIRM', api.current_brief()['brief'])

    # identity, interface and files ---------------------------------------
    def test_same_name_on_another_address_is_proposed_not_merged(self):
        now = NOW
        with store.connect() as db:
            first = store.contact_for(db, 'email', 'laura@example.com', 'Laura', now)
            second = store.contact_for(db, 'email', 'laura@work.example', 'Laura', now)
            self.assertNotEqual(first, second)
            self.assertEqual(db.execute("SELECT contact_id FROM identity_proposals").fetchone()['contact_id'], first)
            store.link_identity(db, 'email', 'laura@work.example', first, 'confirm', now)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM contacts').fetchone()[0], 1)

    def test_linking_one_address_moves_only_its_own_conversations(self):
        self.mail = [self.question(), self.question('m2', sender='Laura <laura@work.example>')]
        self.answers = [self.needs_reply(), self.needs_reply()]
        self.scan()
        with store.connect() as db:
            store.link_identity(db, 'email', 'laura@work.example', 'laura', 'confirm', NOW)  # one person, two addresses
            other = store.contact_for(db, 'email', 'other@example.com', 'Someone else', NOW)
            store.link_identity(db, 'email', 'laura@example.com', other, 'confirm', NOW)
            by_address = {row['address']: row['contact_id'] for row in db.execute('SELECT address, contact_id FROM threads')}
            owners = {item['thread_key']: item['contact_id'] for item in store.query_items(db)}
        self.assertEqual(by_address, {'laura@example.com': other, 'laura@work.example': 'laura'})
        self.assertEqual(sorted(owners.values()), sorted([other, 'laura']))

    def test_older_store_gains_thread_addresses(self):
        with store.connect() as db:
            store.contact_for(db, 'email', 'laura@example.com', 'Laura', NOW)
            db.execute("INSERT INTO threads(key,channel,account,contact_id,updated_at) VALUES('t1','email','gmail','laura','x')")
            db.execute('ALTER TABLE threads DROP COLUMN address')
        with store.connect() as db:
            self.assertEqual(db.execute("SELECT address FROM threads WHERE key='t1'").fetchone()[0], 'laura@example.com')

    # scan claim, times and calendar --------------------------------------------
    def test_only_one_of_two_processes_gets_the_scan(self):
        import sqlite3
        import threading
        with store.connect():
            pass
        barrier, outcomes = threading.Barrier(2), []

        def contender():
            connection = sqlite3.connect(store.database_path(), timeout=10)
            try:
                barrier.wait(timeout=5)
                outcomes.append(store.claim_scan(connection, NOW))
            finally:
                connection.close()
        workers = [threading.Thread(target=contender) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(15)
        self.assertEqual(sum(bool(owner) for owner in outcomes), 1, outcomes)

    def test_an_old_scan_cannot_release_a_newer_claim(self):
        with store.connect() as db:
            first = store.claim_scan(db, NOW)
            self.assertIsNone(store.claim_scan(db, NOW + timedelta(minutes=10)))
            second = store.claim_scan(db, NOW + timedelta(minutes=46))  # the first one crashed or stalled
            self.assertTrue(first and second and first != second)
            self.assertFalse(store.renew_scan(db, first, NOW + timedelta(minutes=47)))
            store.release_scan(db, first)
            self.assertIsNone(store.claim_scan(db, NOW + timedelta(minutes=47)))
            store.release_scan(db, second)
            self.assertTrue(store.claim_scan(db, NOW + timedelta(minutes=47)))

    def test_messages_are_ordered_by_instant_not_local_clock(self):
        self.mail = [message('m1', 'inbox', datetime(2026, 10, 29, 10, tzinfo=timezone(timedelta(hours=2))), 'Free?'),
                     message('m2', 'sent', datetime(2026, 10, 29, 9, 30, tzinfo=timezone.utc), 'Yes!', refs='<m1@example.com>')]
        [thread] = sources.mail_threads('gmail', self.mail, NOW, 7)
        self.assertEqual(thread['last_direction'], 'sent')

    def test_failed_calendar_read_never_reports_a_free_slot(self):
        from integrations.msty.personal import connectors, store as accounts
        calendar = {'accounts': [{'id': 'calendar', 'kind': 'calendar', 'enabled': True}]}
        with patch.object(accounts, 'load', return_value=calendar), \
                patch.object(connectors, 'calendar_events', side_effect=RuntimeError('offline')):
            lookup = sources.calendar_lookup(self.settings)
            event = {'date': '2026-11-01', 'time': '14:00'}
            self.assertEqual([lookup(event, NOW)['status'] for _ in range(2)], ['unknown', 'unknown'])

    def test_tools_validate_mutations_and_never_send(self):
        item = tools.call('commitments_create', {'title': 'Bring the book Saturday', 'contact': 'Paul', 'due_text': 'Saturday'})
        self.assertEqual(item['state'], store.COMMITMENT_OPEN)
        self.assertEqual(tools.call('commitments_list', {})['count'], 1)
        with self.assertRaises(store.InvalidTransition):
            tools.call('attention_snooze', {'id': item['id'], 'until': '2000-01-01'})
        with self.assertRaises(ValueError):
            tools.call('attention_update', {'id': item['id'], 'priority': 'SOMEDAY'})
        done = tools.call('commitments_complete', {'id': item['id'], 'note': 'user said it is done'})
        self.assertEqual(done['state'], store.COMPLETED)
        with self.assertRaises(store.InvalidTransition):
            tools.call('attention_complete', {'id': item['id']})
        names = {t['name'] for t in tools.TOOLS}
        self.assertEqual(names, set(tools.HANDLERS))
        self.assertTrue(set(tools.COMPACT) <= names)
        self.assertFalse(any('send' in name for name in names))

    def test_hand_edited_file_is_kept_before_regeneration(self):
        item = api.create_item('commitment', 'Call the plumber')
        path = self.home / 'commitments' / 'open' / f'{item["id"]}.md'
        path.write_text(path.read_text(encoding='utf-8') + '\nmy note\n', encoding='utf-8')
        api.update_item(item['id'], due_at='2026-11-02')
        conflicts = list((self.home / 'system' / 'conflicts').glob('*.md'))
        self.assertEqual(len(conflicts), 1)
        self.assertIn('my note', conflicts[0].read_text(encoding='utf-8'))
        self.assertIn('due: "2026-11-02"', path.read_text(encoding='utf-8'))

    def test_classifier_must_use_a_local_endpoint(self):
        with self.assertRaises(ValueError):
            config.loopback('https://api.example.com/v1')
        self.assertEqual(config.loopback('http://127.0.0.1:11964/v1'), 'http://127.0.0.1:11964')

    def test_quoted_history_is_not_sent_to_the_model(self):
        text = 'Sounds good.\n\nOn Mon, 26 Oct 2026, Laura wrote:\n> Are you free?\n> secret old text'
        self.assertEqual(sources.strip_quoted(text), 'Sounds good.')

    def test_brief_is_short_and_skips_waiting_details(self):
        api.create_item('waiting', 'Waiting for support', contact='Support')
        text = api.current_brief()['brief']
        self.assertIn('1 conversation waiting on others; no action needed.', text)
        self.assertLess(len(text.splitlines()), 12)

    # Daily rhythm, old conversations, drafts in the owner's style, Google favourites --------
    def question(self, mid='m1', at=NOW - timedelta(hours=5), sender='Laura <laura@example.com>'):
        return message(mid, 'inbox', at, 'Are you free Saturday evening?', sender=sender)

    def needs_reply(self, **overrides):
        return result(**dict(dict(waiting_on='owner', needs_reply=True, reply_kind='question',
                                   summary='Laura asked whether you are free Saturday evening.',
                                   action='Reply about Saturday'), **overrides))

    def test_draft_copies_own_messages_and_is_shown_not_sent(self):
        own = message('s0', 'sent', NOW - timedelta(days=3), 'Holaa Laura!! Cap problema, ens veiem dijous :)',
                      subject='Dinner')
        self.mail = [own, self.question()]
        self.answers = [self.needs_reply(), result()]  # newest conversation is analysed first
        self.scan()
        [call] = self.drafted
        self.assertIn('Holaa Laura!! Cap problema, ens veiem dijous :)', call['examples'])
        self.assertEqual(call['conversation'][-1]['text'], 'Are you free Saturday evening?')
        brief_text = api.current_brief()['brief']
        self.assertIn('Draft (not sent): Hola! Sí, el sábado me va bien. / Alex', brief_text)
        self.scan()
        self.assertEqual(len(self.drafted), 1)  # one draft per item, not one per scan

    def test_old_conversations_are_kept_quietly(self):
        old = NOW - timedelta(days=40)
        self.mail = [self.question(at=old)]
        self.settings['lookback_days'] = 60
        self.answers = [self.needs_reply(urgent=True)]
        scan.run(NOW, settings=self.settings, readers={'email': lambda now: (
            sources.mail_threads('gmail', self.mail, now, 60), {'email:gmail': {'status': 'ok'}})},
            classifier=self.classifier, availability=lambda e, n: {'status': 'free', 'detail': ''},
            drafter=self.drafter, notify=self.notify)
        [item] = self.items()
        self.assertEqual(item['priority'], 'LOW')
        self.assertNotIn('Laura', api.current_brief()['brief'])
        self.assertEqual((self.alerts, self.drafted), ([], []))
        self.assertEqual(api.get_attention_summary(NOW)['counts']['quiet'], 1)

    def test_only_very_important_items_alert_and_only_once(self):
        self.mail = [self.question(), self.question('m2', sender='Marta <marta@example.com>')]
        self.answers = [self.needs_reply(urgent=True), self.needs_reply()]
        self.scan()
        self.assertEqual(len(self.alerts), 1)
        self.assertIn('Laura', self.alerts[0])
        self.scan()
        self.assertEqual(len(self.alerts), 1)

    def test_google_favourites_are_important_and_never_merge_people(self):
        self.mail = [self.question(at=NOW - timedelta(hours=30))]
        self.answers = [self.needs_reply()]
        self.scan()
        (self.home / 'system').mkdir(exist_ok=True)
        (self.home / 'system' / 'google-contacts.csv').write_text(
            'First Name,Last Name,Labels,E-mail 1 - Value\n'
            'Laura,Puig,* myContacts ::: * starred,laura@example.com ::: laura@work.example\n'
            'Marta,Soler,* myContacts,marta@example.com\n', encoding='utf-8')
        self.mail = []
        self.scan(NOW + timedelta(minutes=30))
        [item] = self.items()
        self.assertEqual(item['priority'], 'HIGH')
        self.assertIn('important contact', item['priority_reasons'])
        with store.connect() as db:
            self.assertEqual(db.execute('SELECT name FROM contacts WHERE id=?', ('laura',)).fetchone()['name'], 'Laura Puig')
            owners = {r['address']: r['contact_id'] for r in db.execute('SELECT address, contact_id FROM identities')}
        self.assertEqual(owners['laura@work.example'], 'laura')
        self.assertNotEqual(owners['marta@example.com'], 'laura')
        self.assertEqual(len(self.alerts), 1)  # high and from a favourite

    def test_wrapped_reply_headers_never_reach_examples_or_drafts(self):
        sent = 'Thanks, I will test it.\nEl lun, 26 oct 2026 a las 11:26, Shop (<s@example.com>)\nescribió:\n> Hello'
        self.assertEqual(sources.strip_quoted(sent), 'Thanks, I will test it.')
        draft = 'Hello,\nI will test it.\nthanks El lun, 26 oct 2026 a las 11:26, Shop escribió: > Hello'
        self.assertEqual(sources.strip_quoted_lines(draft), 'Hello,\nI will test it.\nthanks')

    def test_one_brief_a_day_by_default(self):
        from integrations.attention import msty_jobs
        self.assertEqual([job['cron'] for job in msty_jobs.jobs(self.settings)], ['*/30 * * * *', '0 8 * * *'])


if __name__ == '__main__':
    unittest.main()
