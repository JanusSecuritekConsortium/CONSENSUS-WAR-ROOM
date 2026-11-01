"""Offline tests for the Telegram and WhatsApp chat sources: fake accounts, temporary folders, no network."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as Fake
import unittest
import unittest.mock
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.attention import brief, classify, config, scan, sources, store, telegram_user, whatsapp

NOW = datetime(2026, 10, 29, 16, 0, tzinfo=timezone.utc)


def chat_message(mid, from_me, hours_ago, text):
    return {'id': mid, 'from_me': from_me, 'at': (NOW - timedelta(hours=hours_ago)).isoformat(), 'text': text}


def jid(text):
    user, _, server = text.partition('@')
    return Fake(User=user, Server=server)


def wa_text(text):
    from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
    return Message(conversation=text)


class ChatThreadTests(unittest.TestCase):
    def test_chat_becomes_one_conversation_within_the_window(self):
        chats = [{'chat': '42', 'address': '+12025550101', 'name': 'Laura', 'messages': [
            chat_message('1', True, 24 * 90, 'old'), chat_message('3', False, 1, 'Vienes   el sábado?'),
            chat_message('2', True, 3, 'Hola!')]}]
        [thread] = sources.chat_threads('whatsapp', chats, NOW, 60)
        self.assertEqual(thread['channel'], 'whatsapp')
        self.assertEqual([m['text'] for m in thread['messages']], ['Hola!', 'Vienes el sábado?'])
        self.assertEqual(thread['last_direction'], 'inbound')
        self.assertEqual(thread['counterpart_address'], '+12025550101')
        self.assertEqual(thread['key'], sources.chat_threads('whatsapp', chats, NOW, 60)[0]['key'])
        self.assertNotEqual(thread['key'], sources.chat_threads('telegram', chats, NOW, 60)[0]['key'])

    def test_an_edited_message_is_classified_again(self):
        chats = [{'chat': '42', 'address': '+12025550101', 'messages': [chat_message('1', False, 1, 'No hace falta contestar')]}]
        [before] = sources.chat_threads('telegram', chats, NOW, 60)
        chats[0]['messages'][0]['text'] = 'Contéstame hoy, porfa'
        [after] = sources.chat_threads('telegram', chats, NOW, 60)
        self.assertNotEqual(before['fingerprint'], after['fingerprint'])
        self.assertEqual(after['fingerprint'], sources.chat_threads('telegram', chats, NOW, 60)[0]['fingerprint'])

    def test_chats_without_recent_messages_are_left_out(self):
        chats = [{'chat': '1', 'address': '+1', 'messages': [chat_message('1', False, 24 * 61, 'hi')]}]
        self.assertEqual(sources.chat_threads('telegram', chats, NOW, 60), [])

    def test_a_failing_channel_only_marks_itself_unavailable(self):
        def fetch(now, days, limit):
            raise telegram_user.NotSignedIn('session ended')
        threads, status = sources.chat_source('telegram', config.DEFAULTS, fetch)(NOW)
        self.assertEqual((threads, status), ([], {'telegram': {'status': 'unavailable', 'error_type': 'NotSignedIn'}}))

    def test_chat_channels_are_read_only_once_set_up_and_switched_on(self):
        settings = dict(config.DEFAULTS)
        with patch.object(telegram_user, 'configured', return_value=True), \
                patch.object(whatsapp, 'configured', return_value=False):
            self.assertEqual(sorted(sources.default_readers(settings)), ['email', 'telegram'])
            self.assertEqual(sorted(sources.default_readers(dict(settings, telegram_chats=False))), ['email'])


class ChatScanTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patcher = patch.dict(os.environ, {'PERSONAL_ATTENTION_HOME': folder.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = config.load()
        self.prompts, self.drafts = [], []

    def classifier(self, thread):
        self.prompts.append(classify.build_prompt(thread, self.settings, NOW)[1]['content'])
        return classify.validate({'waiting_on': 'owner', 'needs_reply': True, 'reply_kind': 'question',
                                  'informational': False, 'urgent': False, 'confidence': 0.95,
                                  'summary': 'Laura asks about Saturday.', 'action': 'Answer Laura',
                                  'commitments': [], 'appointment': None})

    def drafter(self, item, name, settings, conversation=None, examples=None):
        self.drafts.append(examples)
        return 'Sí!'

    def test_unanswered_whatsapp_question_becomes_a_reply_item(self):
        chats = [{'chat': '34600@s.whatsapp.net', 'address': '+34600', 'name': 'Laura', 'messages': [
            chat_message('1', True, 5, 'Te llamo luego'), chat_message('2', False, 2, 'Vienes el sábado?')]}]
        email = [{'id': 'm1', 'message_id': '<m1@x>', 'references': '', 'subject': 'Report', 'direction': 'sent',
                  'from': 'me@example.com', 'to': 'Ana <ana@example.com>', 'date': (NOW - timedelta(hours=1)).isoformat(),
                  'body': 'Dear Ana, please find attached the report.', 'bulk': False}]
        readers = {
            'whatsapp': sources.chat_source('whatsapp', self.settings, lambda now, days, limit: (chats, {'status': 'ok'})),
            'email': lambda now: (sources.mail_threads('gmail', email, now, 60), {'email:gmail': {'status': 'ok'}}),
        }
        summary = scan.run(NOW, settings=self.settings, readers=readers, classifier=self.classifier,
                           availability=lambda event, now: {'status': 'unknown'}, drafter=self.drafter,
                           notify=lambda *args: None)
        self.assertEqual(summary['sources']['whatsapp'], {'status': 'ok', 'threads': 1})
        self.assertTrue(any(p.startswith('Channel: whatsapp') for p in self.prompts))
        with store.connect() as db:
            [item] = [i for i in store.query_items(db) if i['kind'] == 'reply']
            line = brief.status_line({'last_scan': store.meta_get(db, 'last_scan')}, self.settings)
        self.assertEqual(item['channel'], 'whatsapp')
        self.assertIn('Whatsapp ok', line)
        # The draft copies the owner's chat style before their email style.
        self.assertEqual(self.drafts[0][0], 'Te llamo luego')


class WhatsAppTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        for name, value in (('FOLDER', base), ('MESSAGES', base / 'messages.sqlite3'), ('SESSION', base / 'device.sqlite3'),
                            ('LOCK', base / 'listener.lock')):
            patcher = patch.object(whatsapp, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def live(self, chat, text, from_me=False, group=False, alt='', mid='M1', at=None):
        source = Fake(Chat=jid(chat), IsGroup=group, IsFromMe=from_me, SenderAlt=jid(alt), RecipientAlt=jid(alt))
        info = Fake(MessageSource=source, ID=mid, Pushname='Laura', Timestamp=int((at or NOW).timestamp()))
        whatsapp.live_message(Fake(Info=info, Message=wa_text(text) if isinstance(text, str) else text))

    def test_only_personal_text_messages_are_stored(self):
        self.assertFalse(whatsapp.configured())
        self.live('12025550101@s.whatsapp.net', 'Vienes el sábado?')
        self.live('12345@g.us', 'group chatter', group=True, mid='G1')
        self.live('status@broadcast', 'a status', mid='S1')
        from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
        self.live('12025550101@s.whatsapp.net', Message(), mid='R1')  # a reaction or protocol message
        chats, status = whatsapp.fetch(whatsapp.utcnow(), 60, 60)
        self.assertEqual(status, {'status': 'ok', 'chats': 1})
        [chat] = chats
        self.assertEqual((chat['address'], chat['name']), ('+12025550101', 'Laura'))
        self.assertEqual([m['text'] for m in chat['messages']], ['Vienes el sábado?'])

    def test_hidden_number_chats_take_the_number_when_known(self):
        self.live('99887766@lid', 'Hola', alt='12025550102@s.whatsapp.net')
        self.live('11223344@lid', 'Hi', mid='M2')
        chats, _ = whatsapp.fetch(NOW, 60, 60)
        self.assertEqual(sorted(c['address'] for c in chats), ['+12025550102', 'whatsapp:11223344'])

    def test_history_sync_is_stored_once(self):
        def item(mid, from_me, text):
            return Fake(message=Fake(key=Fake(ID=mid, fromMe=from_me), message=wa_text(text),
                                     messageTimestamp=int((NOW - timedelta(hours=2)).timestamp())))
        data = Fake(pushnames=[], phoneNumberToLidMappings=[Fake(lidJID='5555@lid', pnJID='12025550103@s.whatsapp.net')],
                    conversations=[Fake(ID='5555@lid', pnJID='', name='Marc', displayName='', messages=[
                                        item('H1', False, 'Quedamos?'), item('H2', True, 'Vale')]),
                                   Fake(ID='777@g.us', pnJID='', name='Group', displayName='', messages=[
                                        item('H3', False, 'group')])])
        whatsapp.history(Fake(Data=data))
        whatsapp.history(Fake(Data=data))
        [chat], _ = whatsapp.fetch(NOW, 60, 60)
        self.assertEqual((chat['address'], chat['name']), ('+12025550103', 'Marc'))
        self.assertEqual([(m['from_me'], m['text']) for m in chat['messages']], [(False, 'Quedamos?'), (True, 'Vale')])

    def test_a_stopped_or_restricted_link_is_reported(self):
        self.live('12025550101@s.whatsapp.net', 'Hola')
        _, status = whatsapp.fetch(whatsapp.utcnow() + timedelta(hours=2), 60, 60)  # heartbeat uses the real clock
        self.assertEqual(status['status'], 'stale')
        whatsapp.set_meta(state='temporarily_banned')
        chats, status = whatsapp.fetch(NOW, 60, 60)
        self.assertEqual((status['status'], status['error_type'], len(chats)), ('unavailable', 'temporarily_banned', 1))
        self.assertIn('not linked', whatsapp.listen())

    def test_heartbeat_records_a_connected_listener(self):
        stop = Fake(wait=unittest.mock.Mock(side_effect=[False, True]))
        whatsapp.heartbeat(Fake(is_connected=True), stop)
        self.assertIsNotNone(whatsapp.meta('heartbeat'))

    def test_message_text_and_media_labels(self):
        from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
        voice = Message()
        voice.audioMessage.PTT = True
        wrapped = Message()
        wrapped.ephemeralMessage.message.extendedTextMessage.text = 'disappearing'
        photo = Message()
        photo.imageMessage.caption = ''
        self.assertEqual([whatsapp.text_of(m) for m in (voice, wrapped, photo, Message())],
                         ['(voice note)', 'disappearing', '(photo)', None])
        self.assertEqual(whatsapp.stamp(1_700_000_000_000), whatsapp.stamp(1_700_000_000))


class TelegramTests(unittest.TestCase):
    def test_address_prefers_the_phone_number(self):
        self.assertEqual(telegram_user.address(Fake(phone='12025550101', username='laura', id=1)), '+12025550101')
        self.assertEqual(telegram_user.address(Fake(phone=None, username='Laura', id=1)), '@laura')
        self.assertEqual(telegram_user.address(Fake(phone=None, username=None, id=7)), 'telegram:7')

    def test_message_text_and_media_labels(self):
        blank = dict(action=None, message='', voice=None, video_note=None, photo=None, video=None, sticker=None,
                     gif=None, contact=None, geo=None, poll=None, document=None)
        self.assertEqual(telegram_user.text_of(Fake(**dict(blank, message='Hola'))), 'Hola')
        self.assertEqual(telegram_user.text_of(Fake(**dict(blank, voice=object(), document=object()))), '(voice note)')
        self.assertIsNone(telegram_user.text_of(Fake(**dict(blank, action=object()))))

    def test_reading_without_a_session_is_refused(self):
        with patch.object(telegram_user, 'credentials', return_value={}):
            self.assertFalse(telegram_user.configured())
            with self.assertRaises(telegram_user.NotSignedIn):
                telegram_user.fetch(NOW, 60, 60)


if __name__ == '__main__':
    unittest.main()
