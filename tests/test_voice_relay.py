import json
import sqlite3
import pytest
from integrations.msty.personal import voice_relay as relay


@pytest.fixture
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(relay.store,'ROOT',tmp_path)


def update(uid=100, sender=42):
    return {'update_id':uid,'message':{'chat':{'id':42,'type':'private'},'from':{'id':sender},'message_id':7,'text':'No hagas cambios'}}


def test_persist_before_ack_and_deduplicate(isolated):
    relay.enqueue([update(),update(),update(101,12)],'42')
    with relay.database() as db:
        assert db.execute('SELECT count(*) FROM inbox').fetchone()[0]==1
        assert db.execute('SELECT offset FROM cursor').fetchone()[0]==102


def test_dispatch_uncertainty_does_not_repeat(isolated,monkeypatch):
    relay.enqueue([update()],'42')
    relay.set_state(100,'prepared',prompt='test')
    calls=[]
    class Client:
        def initialize(self):pass
        def call(self,*args):calls.append(args);raise TimeoutError()
        def close(self):pass
    monkeypatch.setattr(relay,'Client',Client)
    monkeypatch.setattr(relay,'final_reply',lambda *args:None)
    path=relay.store.ROOT/'msty.db'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE messages (content TEXT)')
    monkeypatch.setattr(relay,'database_path',lambda:path)
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    with pytest.raises(TimeoutError):relay.process(row,{'chat_id':'42'})
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    assert row['state']=='awaiting_reply'
    relay.process(row,{'chat_id':'42'})
    assert len(calls)==1


def test_unknown_send_not_retried(isolated,monkeypatch):
    relay.enqueue([update()],'42');relay.set_state(100,'reply_ready',reply='test')
    def failed(*args):raise TimeoutError()
    monkeypatch.setattr(relay,'api',failed)
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    with pytest.raises(TimeoutError):relay.process(row,{'chat_id':'42'})
    with relay.database() as db:assert db.execute('SELECT state FROM inbox').fetchone()[0]=='delivery_uncertain'


def test_stable_request_key_and_bounded_plain_text():
    prompt=relay.prompt_for(update()['message'],{'chat_id':'42'})
    assert relay.receipt_marker(update()['message'],{'chat_id':'42'}) in prompt
    assert 'telegram:42:7' not in prompt
    assert len(relay.plain_reply('😀'*5000).encode('utf-16-le'))<=8192


def test_forwarded_text_is_reference_not_authorization():
    message=update()['message'];message['forward_origin']={'type':'user'}
    assert 'no una orden autorizada' in relay.prompt_for(message,{'chat_id':'42'})


def test_reply_waits_for_final_text_and_stays_in_turn(tmp_path,monkeypatch):
    path=tmp_path/'messages.db'
    monkeypatch.setattr(relay,'database_path',lambda:path)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE messages (conversation_id TEXT, sequence INTEGER, role TEXT, content TEXT, tool_calls TEXT, created_at TEXT)')
        db.executemany('INSERT INTO messages VALUES (?,?,?,?,?,?)',[
            ('a',1,'user','receipt-one',None,'1'),
            ('a',2,'assistant','Checking now',json.dumps([{'status':'completed'}]),'2'),
            ('b',1,'assistant','Unrelated reply',None,'3')])
    assert relay.final_reply('receipt-one') is None
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?)',('a',3,'assistant','Finished',None,'4'))
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?)',('a',4,'user','Next request',None,'5'))
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?)',('a',5,'assistant','Next answer',None,'6'))
    assert relay.final_reply('receipt-one')=='Finished'
    assert relay.final_reply('unknown-receipt') is None


def test_redacted_prompt_matching_preserves_privacy():
    prompt='receipt-example\nUna prueba suficientemente larga para identificar el mensaje sin datos privados. 😀'
    original='[MCP Client]: '+prompt
    metadata=json.dumps({'dataProtection':{'redactions':[{'start':14,'end':29,'replacement':'[redacted: private person]'}]}})
    content=original[:14]+'[redacted: private person]'+original[29:]
    assert relay.matches_redacted_prompt(content,metadata,prompt)
    assert not relay.matches_redacted_prompt(content,metadata,prompt+' diferente')
    assert not relay.matches_redacted_prompt(content,'{}',prompt)


def test_redacted_receipt_requires_unique_new_turn(tmp_path,monkeypatch):
    path=tmp_path/'msty.db';monkeypatch.setattr(relay,'database_path',lambda:path)
    prompt='opaque\nThis is a harmless local test with enough visible text to match safely.'
    content='[MCP Client]: [redacted: private person]\n'+prompt.split('\n')[1]
    metadata=json.dumps({'dataProtection':{'redactions':[{'start':13,'end':20,'replacement':'[redacted: private person]'}]}})
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE conversations (id TEXT,bot_id TEXT)')
        db.execute('INSERT INTO conversations VALUES (?,?)',('a',relay.BOT_ID))
        db.execute('CREATE TABLE messages (conversation_id TEXT,sequence INTEGER,role TEXT,content TEXT,tool_calls TEXT,created_at TEXT,metadata TEXT)')
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',1,'user',content,None,'1',metadata))
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',2,'assistant','Done',None,'2',None))
    assert relay.final_reply('opaque',prompt,0)=='Done'
    assert relay.final_reply('opaque',prompt,2) is None
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',3,'user',content,None,'3',metadata))
    assert relay.final_reply('opaque',prompt,0) is None


def test_receiver_polls_choices_while_agent_waits(isolated,monkeypatch):
    from contextlib import nullcontext
    relay.enqueue([update()],'42');relay.set_state(100,'prepared',prompt='waiting')
    choices=update(101);choices['message']['text']='1'
    configs=iter([{'telegram_voice_relay_enabled':True},{'telegram_voice_relay_enabled':False}])
    monkeypatch.setattr(relay.store,'load',lambda:next(configs))
    monkeypatch.setattr(relay,'single_instance',nullcontext)
    monkeypatch.setattr(relay,'enabled',lambda:True)
    monkeypatch.setattr(relay,'telegram_route',lambda:{'chat_id':'42'})
    class Client:
        def initialize(self):raise RuntimeError()
        def close(self):pass
    monkeypatch.setattr(relay,'Client',Client)
    calls=[]
    def api(route,method,data):calls.append(data);return [choices]
    monkeypatch.setattr(relay,'api',api)
    processed=[];monkeypatch.setattr(relay,'process',lambda row,route:processed.append(row['update_id']))
    monkeypatch.setattr(relay.time,'sleep',lambda seconds:None)
    relay.run()
    assert processed==[101] and calls[0]['timeout']==0

def test_stale_command_not_dispatched(isolated,monkeypatch):
    old=update();old['message']['date']=1
    relay.enqueue([old],'42')
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    relay.process(row,{'chat_id':'42'})
    with relay.database() as db:
        row=dict(db.execute('SELECT * FROM inbox').fetchone())
    assert row['error']=='stale_request' and row['state']=='reply_ready'
