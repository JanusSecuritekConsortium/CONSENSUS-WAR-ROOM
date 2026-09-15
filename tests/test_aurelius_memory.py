from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from integrations.msty import aurelius_memory as memory
from integrations.mcp.consensus_mcp_server import handle_jsonrpc


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/'msty.db'
        with sqlite3.connect(self.path) as db:
            db.executescript('''
            CREATE TABLE memory_packs(id PRIMARY KEY,title,archived DEFAULT 0,current_revision_id,updated_at);
            CREATE TABLE memory_pack_revisions(id PRIMARY KEY,pack_id,revision_number,state_json,revision_reason,created_at,UNIQUE(pack_id,revision_number));
            CREATE TABLE memory_pack_search_docs(id INTEGER PRIMARY KEY,pack_id UNIQUE,revision_id,title,summary,tags_json,content_text,updated_at);
            CREATE VIRTUAL TABLE memory_pack_fts USING fts5(title,summary,tags,content_text);
            ''')
            state={'summary':'','facts':[],'constraints':[],'decisions':[],'open_tasks':[],'open_questions':[],'artifacts':[],'changes_since_last_revision':[],'evidence_refs':[]}
            for pack in (memory.PACK_ID,'unrelated-pack'):
                db.execute('INSERT INTO memory_packs(id,title,current_revision_id) VALUES(?,?,?)',(pack,pack,pack+'-first'))
                db.execute('INSERT INTO memory_pack_revisions(id,pack_id,revision_number,state_json) VALUES(?,?,?,?)',(pack+'-first',pack,1,json.dumps(state)))

    def tearDown(self):
        self.temp.cleanup()

    def test_cross_connection_recall_and_revision(self):
        saved=memory.remember('imaginary spaceship','Call of Cathulu','telegram',db_path=self.path)
        self.assertTrue(saved['saved'])
        recalled=memory.recall('imaginary spaceship',db_path=self.path)
        self.assertEqual(recalled['facts'][0]['value'],'Call of Cathulu')
        self.assertEqual(recalled['revision'],2)
        self.assertEqual(memory.recall('imaginary_spaceship',db_path=self.path)['facts'][0]['value'],'Call of Cathulu')

    def test_updates_preserve_other_keys_and_packs(self):
        memory.remember('spaceship','Finch',db_path=self.path)
        memory.remember('favorite_color','green',db_path=self.path)
        memory.remember('spaceship','Cathulu','mobile',db_path=self.path)
        result=memory.recall(db_path=self.path)
        self.assertEqual(len(result['facts']),2)
        self.assertEqual(memory.recall('spaceship',db_path=self.path)['facts'][0]['value'],'Cathulu')
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_pack_revisions WHERE pack_id='unrelated-pack'").fetchone()[0],1)

    def test_retry_is_idempotent(self):
        first=memory.remember('fact','value',db_path=self.path)
        second=memory.remember('fact','value',db_path=self.path)
        self.assertEqual(first['revision'],second['revision'])
        self.assertTrue(second['unchanged'])

    def test_concurrent_writes_no_lost_facts(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda i:memory.remember('fact_'+str(i),'value '+str(i),db_path=self.path),range(10)))
        self.assertTrue(all(result['saved'] for result in results))
        self.assertEqual(len(memory.recall(db_path=self.path)['facts']),10)

    def test_forget_keeps_history(self):
        memory.remember('spaceship','Finch',db_path=self.path)
        self.assertTrue(memory.forget('spaceship',db_path=self.path)['forgotten'])
        self.assertFalse(memory.recall('spaceship',db_path=self.path)['found'])
        with sqlite3.connect(self.path) as db:
            self.assertIn('Finch',db.execute('SELECT state_json FROM memory_pack_revisions WHERE pack_id=? AND revision_number=2',(memory.PACK_ID,)).fetchone()[0])

    def test_input_safety(self):
        for key,value in (('../../file','value'),('api_key','not-for-memory'),('fact','password=secret'),('fact','x'*2001)):
            with self.assertRaises(ValueError):memory.remember(key,value,db_path=self.path)
        with self.assertRaises(ValueError):memory.remember('fact','value','other',db_path=self.path)

    def test_archived_pack_not_written(self):
        with sqlite3.connect(self.path) as db:db.execute('UPDATE memory_packs SET archived=1 WHERE id=?',(memory.PACK_ID,))
        with self.assertRaises(ValueError):memory.remember('fact','value',db_path=self.path)

    def test_native_search_index(self):
        memory.remember('spaceship','Cathulu',db_path=self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM memory_pack_fts WHERE memory_pack_fts MATCH 'Cathulu'").fetchone()[0],1)

    def test_recall_is_read_only(self):
        memory.remember('spaceship','Cathulu',db_path=self.path)
        before=self.path.read_bytes()
        memory.recall('spaceship',db_path=self.path)
        self.assertEqual(before,self.path.read_bytes())

    def test_failed_index_update_rolls_back_save(self):
        with patch.object(memory,'_index',side_effect=sqlite3.OperationalError('index unavailable')):
            with self.assertRaises(sqlite3.OperationalError):memory.remember('fact','value',db_path=self.path)
        self.assertFalse(memory.recall('fact',db_path=self.path)['found'])
        self.assertEqual(memory.recall(db_path=self.path)['revision'],1)

    def test_mcp_handoff(self):
        with patch.object(memory,'database_path',return_value=self.path):
            response=handle_jsonrpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'aurelius_memory_remember','arguments':{'key':'spaceship','value':'Cathulu','origin':'telegram'}}})
            self.assertTrue(json.loads(response['result']['content'][0]['text'])['saved'])
            response=handle_jsonrpc({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'aurelius_memory_recall','arguments':{'query':'spaceship'}}})
            self.assertEqual(json.loads(response['result']['content'][0]['text'])['facts'][0]['value'],'Cathulu')


if __name__=='__main__':unittest.main()
