"""Memory pack building with synthetic notes and a fake local model."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.msty import memory_packs as mp

CHAT = '''---
title: "Moving flat"
originalDate: 2025-03-01
---

## You
`2025-03-01 10:00` | `id:1` ^1

I am moving to Lisbon in May and need a lawyer.

---

## ChatGPT
`2025-03-01 10:01` | `id:2` ^2

General advice the pack should not keep.
'''


def fake_model(state):
    calls = []

    def post(url, json=None, timeout=None):
        calls.append(json)

        class Response:
            def raise_for_status(self):
                pass

            def json(self_inner):
                return {'message': {'content': __import__('json').dumps(state)}}
        return Response()
    post.calls = calls
    return post


class MemoryPackTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_a_failed_topic_is_retried_once_and_the_rest_continue(self):
        note = self.root / 'n.md'
        note.write_text(CHAT, encoding='utf-8')
        (self.root / 'topics.json').write_text(json.dumps({'Bad': [str(note)], 'Good': [str(note)]}), encoding='utf-8')
        good = fake_model({'durable_summary': 'ok', 'facts': [], 'constraints': [], 'decisions': [],
                           'open_tasks': [], 'artifacts': [], 'tags': []})
        calls = []

        def post(url, json=None, timeout=None):
            calls.append(1)
            if len(calls) <= 2:
                raise mp.requests.ConnectionError('server restarting')
            return good(url, json=json, timeout=timeout)
        waits = []
        with patch.object(mp, 'OUTPUT', self.root):
            result = mp.build(post=post, sleep=waits.append)
        self.assertEqual(result, {'built': ['Good'], 'failed': ['Bad']})
        self.assertEqual(waits, [60])

    def test_install_writes_packs_and_search_index_once(self):
        import sqlite3
        db_path = self.root / 'msty.db'
        db = sqlite3.connect(db_path)
        db.executescript('''
            CREATE TABLE memory_packs (id TEXT PRIMARY KEY, title TEXT NOT NULL, source_conversation_id TEXT,
              current_revision_id TEXT, archived INTEGER NOT NULL DEFAULT 0, created_at TEXT, updated_at TEXT);
            CREATE TABLE memory_pack_revisions (id TEXT PRIMARY KEY, pack_id TEXT NOT NULL, revision_number INTEGER NOT NULL,
              state_json TEXT NOT NULL DEFAULT '{}', created_from_brief_id TEXT, source_conversation_id TEXT,
              revision_reason TEXT, created_at TEXT, UNIQUE(pack_id, revision_number));
            CREATE TABLE memory_pack_search_docs (id INTEGER PRIMARY KEY AUTOINCREMENT, pack_id TEXT NOT NULL UNIQUE,
              revision_id TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL, tags_json TEXT NOT NULL DEFAULT '[]',
              content_text TEXT NOT NULL DEFAULT '', updated_at TEXT);
            CREATE VIRTUAL TABLE memory_pack_fts USING fts5(title, summary, tags, content_text);''')
        db.close()
        state = {'durable_summary': 'Moving to Lisbon.', 'facts': [{'key': 'Move', 'value': 'Lisbon in May'}],
                 'open_tasks': [{'title': 'Find a lawyer', 'detail': ''}], 'artifacts': [{'title': 'Lease', 'detail': 'draft'}],
                 'tags': ['home']}
        pack = self.root / 'Home.mc.mem'
        pack.write_text(json.dumps(mp.envelope('Home', state, datetime(2026, 11, 2, tzinfo=timezone.utc))), encoding='utf-8')
        self.assertEqual(mp.install(db_path, [pack])['added'], ['Home'])
        self.assertEqual(mp.install(db_path, [pack])['unchanged'], ['Home'])
        state['facts'].append({'key': 'Budget', 'value': 'Tight'})
        pack.write_text(json.dumps(mp.envelope('Home', state, datetime(2026, 11, 3, tzinfo=timezone.utc))), encoding='utf-8')
        self.assertEqual(mp.install(db_path, [pack])['updated'], ['Home'])
        db = sqlite3.connect(db_path)
        stored = json.loads(db.execute('SELECT state_json FROM memory_pack_revisions r JOIN memory_packs p '
                                       'ON p.current_revision_id=r.id').fetchone()[0])
        self.assertEqual(stored['facts'][0]['status'], 'current')
        self.assertEqual([stored['open_tasks'][0]['status'], stored['artifacts'][0]['status']], ['open', 'current'])
        self.assertEqual(db.execute("SELECT count(*) FROM memory_pack_fts WHERE memory_pack_fts MATCH 'budget'").fetchone()[0], 1)
        self.assertEqual(db.execute('SELECT count(*) FROM memory_pack_search_docs').fetchone()[0], 1)
        db.close()

    def test_chat_digest_keeps_only_the_owners_words(self):
        path = self.root / '2026-07-02-Moving.md'
        path.write_text(CHAT, encoding='utf-8')
        text = mp.digest(mp.read_note(path))
        self.assertIn('## Moving flat (2025-03-01)', text)
        self.assertIn('[OWNER] I am moving to Lisbon in May and need a lawyer.', text)
        self.assertNotIn('General advice', text)

    def test_state_is_clipped_to_msty_limits(self):
        state = mp.clip_state({'durable_summary': 'x' * 2000, 'facts': [{'key': 'k', 'value': 'v'}] * 40 + [{'key': ''}],
                               'tags': ['A', 'a', ' b '] + [f't{i}' for i in range(20)]})
        self.assertEqual(len(state['durable_summary']), 1200)
        self.assertEqual(len(state['facts']), 32)
        self.assertEqual(state['tags'][:2], ['a', 'b'])
        self.assertEqual(len(state['tags']), 16)

    def test_build_writes_one_pack_per_topic_with_stable_ids(self):
        note = self.root / 'n.md'
        note.write_text(CHAT, encoding='utf-8')
        (self.root / 'topics.json').write_text(json.dumps({'Home': [str(note)]}), encoding='utf-8')
        state = {'durable_summary': 'Moving to Lisbon.', 'facts': [{'key': 'Move', 'value': 'Lisbon in May'}],
                 'constraints': [], 'decisions': [], 'open_tasks': [{'title': 'Find a lawyer', 'detail': ''}],
                 'artifacts': [], 'tags': ['home']}
        post = fake_model(state)
        now = datetime(2026, 11, 2, tzinfo=timezone.utc)
        with patch.object(mp, 'OUTPUT', self.root):
            self.assertEqual(mp.build(post=post, now=now), {'built': ['Home'], 'failed': []})
            first = json.loads((self.root / 'Home.mc.mem').read_text(encoding='utf-8'))
            self.assertEqual(mp.build(post=post, now=now)['built'], [])  # already built
            mp.build(['Home'], post=post, now=now)
            second = json.loads((self.root / 'Home.mc.mem').read_text(encoding='utf-8'))
        self.assertEqual(first['pack']['title'], 'Home')
        self.assertEqual(first['pack']['currentRevisionId'], first['revisions'][0]['id'])
        self.assertEqual(first['revisions'][0]['state']['open_tasks'][0]['title'], 'Find a lawyer')
        self.assertEqual(first, second)
        self.assertEqual(len(post.calls), 2)
        self.assertTrue(post.calls[0]['options']['num_ctx'] >= 16384)


if __name__ == '__main__':
    unittest.main()
