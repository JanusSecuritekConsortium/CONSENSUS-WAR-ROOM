"""Attaching memory packs and approving Msty Go memory suggestions, against a synthetic Msty Go database."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.msty import memory_packs as mp, memory_review as mr

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
SCHEMA = '''
CREATE TABLE memory_packs (id TEXT PRIMARY KEY, title TEXT NOT NULL, source_conversation_id TEXT,
  current_revision_id TEXT, archived INTEGER NOT NULL DEFAULT 0, created_at TEXT, updated_at TEXT);
CREATE TABLE memory_pack_revisions (id TEXT PRIMARY KEY, pack_id TEXT NOT NULL, revision_number INTEGER NOT NULL,
  state_json TEXT NOT NULL DEFAULT '{}', created_from_brief_id TEXT, source_conversation_id TEXT,
  revision_reason TEXT, created_at TEXT, UNIQUE(pack_id, revision_number));
CREATE TABLE memory_pack_search_docs (id INTEGER PRIMARY KEY AUTOINCREMENT, pack_id TEXT NOT NULL UNIQUE,
  revision_id TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL, tags_json TEXT NOT NULL DEFAULT '[]',
  content_text TEXT NOT NULL DEFAULT '', updated_at TEXT);
CREATE VIRTUAL TABLE memory_pack_fts USING fts5(title, summary, tags, content_text);
CREATE TABLE memory_mounts (owner_type TEXT NOT NULL, owner_id TEXT NOT NULL, pack_id TEXT NOT NULL, created_at TEXT,
  PRIMARY KEY (owner_type, owner_id, pack_id));
CREATE TABLE chat_folders (id TEXT PRIMARY KEY, parent_id TEXT, name TEXT, learning_enabled INTEGER DEFAULT 0,
  default_pack_id TEXT, sort_order INTEGER, created_at TEXT, updated_at TEXT, workspace_path TEXT);
CREATE TABLE bots (id TEXT PRIMARY KEY, name TEXT);
CREATE TABLE folder_memory_candidates (id TEXT PRIMARY KEY, folder_id TEXT NOT NULL, source_conversation_id TEXT,
  source_brief_id TEXT, kind TEXT NOT NULL, key TEXT, value TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT, updated_at TEXT, source_excerpt TEXT, rationale TEXT);
'''


class MemoryReviewTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.db_path = self.root / 'msty.db'
        db = sqlite3.connect(self.db_path)
        db.executescript(SCHEMA)
        db.execute("INSERT INTO chat_folders(id,name) VALUES('f1','Home'),('f2','Hobbies')")
        db.execute("INSERT INTO bots VALUES('b1','Assistant')")
        db.execute("INSERT INTO folder_memory_candidates(id,folder_id,kind,key,value,created_at) VALUES"
                   "('c1','f1','fact','Move','Lisbon in May','1'),('c2','f1','task',NULL,'Call the lawyer','2'),"
                   "('c3','f1','fact',NULL,'Likes tea','3')")
        db.commit()
        for title in ('Home', 'Health'):
            mp.write_revision(db, mp.stable_id('pack', title), title, mp.stable_id('rev', title),
                              mp.stored_state({'durable_summary': title}, title), 'test', 'now')
        db.commit()
        db.close()
        output = patch.object(mp, 'OUTPUT', self.root)
        output.start()
        self.addCleanup(output.stop)

    def query(self, sql, *args):
        db = sqlite3.connect(self.db_path)
        try:
            return db.execute(sql, args).fetchall()
        finally:
            db.close()

    def test_mount_attaches_packs_sets_default_and_learning_once(self):
        plan = {'folders': {'Home': ['Home', 'Health'], 'Nowhere': ['Home']}, 'bots': ['Health', 'Gone']}
        result = mr.mount(self.db_path, plan, now=NOW)
        self.assertEqual(result, {'attached': 3, 'missing': ['Nowhere', 'Gone']})
        self.assertEqual(mr.mount(self.db_path, plan, now=NOW)['attached'], 0)
        self.assertEqual(self.query("SELECT learning_enabled, default_pack_id FROM chat_folders WHERE id='f1'"),
                         [(1, mp.stable_id('pack', 'Home'))])
        self.assertEqual(self.query("SELECT learning_enabled FROM chat_folders WHERE id='f2'"), [(0,)])

    def test_remember_adds_to_the_default_pack_and_skip_dismisses(self):
        mr.mount(self.db_path, {'folders': {'Home': ['Home']}}, now=NOW)
        self.assertEqual(mr.decide('c1', True, db_path=self.db_path, now=NOW), 'Remembered in Home: Move')
        self.assertIn('Remembered in Home', mr.decide('c2', True, db_path=self.db_path, now=NOW))
        self.assertEqual(mr.decide('c3', False, db_path=self.db_path, now=NOW), 'Not remembered: Likes tea')
        self.assertEqual(mr.decide('c1', True, db_path=self.db_path, now=NOW), 'Already accepted.')
        state = json.loads(self.query('SELECT state_json FROM memory_pack_revisions r JOIN memory_packs p '
                                      "ON p.current_revision_id=r.id WHERE p.title='Home'")[0][0])
        self.assertEqual([(f['key'], f['value']) for f in state['facts']], [('Move', 'Lisbon in May')])
        self.assertEqual(state['open_tasks'][0]['title'], 'Call the lawyer')
        self.assertEqual(self.query("SELECT count(*) FROM memory_pack_fts WHERE memory_pack_fts MATCH 'lisbon'"), [(1,)])
        self.assertEqual(self.query('SELECT status FROM folder_memory_candidates ORDER BY id'),
                         [('accepted',), ('accepted',), ('dismissed',)])

    def test_a_folder_without_a_pack_is_not_written(self):
        self.assertIn('no memory pack', mr.decide('c1', True, db_path=self.db_path, now=NOW))
        self.assertEqual(self.query("SELECT status FROM folder_memory_candidates WHERE id='c1'"), [('pending',)])

    def test_each_suggestion_is_asked_once(self):
        sent = []
        self.assertEqual(mr.ask(2, db_path=self.db_path, now=NOW, send=lambda text, cid, now: sent.append((cid, text))), 2)
        self.assertEqual(mr.ask(5, db_path=self.db_path, now=NOW, send=lambda text, cid, now: sent.append((cid, text))), 1)
        self.assertEqual([cid for cid, _ in sent], ['c1', 'c2', 'c3'])
        self.assertEqual(sent[0][1], 'Remember this? (Home, fact)\nMove: Lisbon in May')

    def test_button_reaches_the_review(self):
        from integrations.msty.personal import conversation
        with patch.object(mr, 'decide', return_value='Remembered in Home: Move') as decide:
            reply = conversation.answer(None, None, 'en', 'k', callback=('memory', {'c': 'c1', 'keep': True}))
        decide.assert_called_once_with('c1', True)
        self.assertEqual(reply['text'], 'Remembered in Home: Move')


if __name__ == '__main__':
    unittest.main()
