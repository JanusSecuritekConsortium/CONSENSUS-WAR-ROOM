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
        db.execute('CREATE TABLE messages (conversation_id TEXT, sequence INTEGER, role TEXT, content TEXT, tool_calls TEXT, created_at TEXT, metadata TEXT)')
        db.executemany('INSERT INTO messages VALUES (?,?,?,?,?,?,NULL)',[
            ('a',1,'user','receipt-one',None,'1'),
            ('a',2,'assistant','Checking now',json.dumps([{'status':'completed'}]),'2'),
            ('b',1,'assistant','Unrelated reply',None,'3')])
    assert relay.final_reply('receipt-one') is None
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,NULL)',('a',3,'assistant','Finished',None,'4'))
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,NULL)',('a',4,'user','Next request',None,'5'))
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,NULL)',('a',5,'assistant','Next answer',None,'6'))
    assert relay.final_reply('receipt-one')=='Finished'
    assert relay.final_reply('unknown-receipt') is None


def test_reply_skips_context_compaction_summary(tmp_path,monkeypatch):
    path=tmp_path/'messages.db'
    monkeypatch.setattr(relay,'database_path',lambda:path)
    summary=json.dumps({'excludeFromContext':True,'messageType':'context_compaction'})
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE messages (conversation_id TEXT, sequence INTEGER, role TEXT, content TEXT, tool_calls TEXT, created_at TEXT, metadata TEXT)')
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',1,'user','receipt-two',None,'1',None))
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',2,'assistant','## Current Progress',None,'2',summary))
    assert relay.final_reply('receipt-two') is None
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',3,'assistant','Three unread emails...',None,'3','{}'))
    assert relay.final_reply('receipt-two')=='Three unread emails...'


def test_reply_delivers_failed_turn_error_with_tool_calls(tmp_path,monkeypatch):
    path=tmp_path/'messages.db'
    monkeypatch.setattr(relay,'database_path',lambda:path)
    calls=json.dumps([{'name':'email_search','status':'completed'}])
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE messages (conversation_id TEXT, sequence INTEGER, role TEXT, content TEXT, tool_calls TEXT, created_at TEXT, metadata TEXT)')
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',1,'user','receipt-three',None,'1',None))
        db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('a',2,'assistant','  **Error:** The response stopped before finishing.',calls,'2','{}'))
    assert relay.final_reply('receipt-three').strip().startswith('**Error:**')


def test_prompt_steers_telegram_away_from_in_app_prompts():
    prompt=relay.prompt_for(update()['message'],{'chat_id':'42'})
    assert 'request_clarification' in prompt and 'email_accounts' in prompt


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

def test_msty_outage_alerts_once_and_reports_recovery(isolated,monkeypatch):
    sent=[];monkeypatch.setattr(relay,'api',lambda route,method,data:sent.append(data['text']))
    route={'chat_id':'42'}
    for failures in range(1,relay.MSTY_ALERT_AFTER):relay.msty_alert(route,False,failures,'unreachable')
    assert sent==[]
    relay.msty_alert(route,False,relay.MSTY_ALERT_AFTER,'unauthorized')
    relay.msty_alert(route,False,relay.MSTY_ALERT_AFTER+1,'unauthorized')
    assert len(sent)==1 and 'token' in sent[0] and 'voice_setup' in sent[0]
    relay.msty_alert(route,True,0,None);relay.msty_alert(route,True,0,None)
    assert len(sent)==2 and 'again' in sent[1]


def test_msty_alert_retries_when_telegram_send_fails(isolated,monkeypatch):
    def failed(*args):raise RuntimeError('Telegram transport failed')
    monkeypatch.setattr(relay,'api',failed)
    relay.msty_alert({'chat_id':'42'},False,relay.MSTY_ALERT_AFTER,'unreachable')
    sent=[];monkeypatch.setattr(relay,'api',lambda route,method,data:sent.append(data['text']))
    relay.msty_alert({'chat_id':'42'},False,relay.MSTY_ALERT_AFTER+1,'unreachable')
    assert len(sent)==1 and 'minutes' in sent[0]


def test_msty_failure_tells_refused_token_from_unreachable():
    import requests
    def wrapped(inner):
        try:
            try:raise inner
            except Exception:raise RuntimeError('Local Msty MCP request failed') from None
        except RuntimeError as error:return error
    refused=requests.HTTPError(response=type('R',(),{'status_code':401})())
    assert relay.msty_failure(wrapped(refused))=='unauthorized'
    assert relay.msty_failure(wrapped(requests.ConnectionError()))=='unreachable'
    assert relay.msty_failure(ValueError('Configure the local MCP bearer token'))=='unreachable'


def test_stale_command_not_dispatched(isolated,monkeypatch):
    old=update();old['message']['date']=1
    relay.enqueue([old],'42')
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    relay.process(row,{'chat_id':'42'})
    with relay.database() as db:
        row=dict(db.execute('SELECT * FROM inbox').fetchone())
    assert row['error']=='stale_request' and row['state']=='reply_ready'


def test_missing_agent_config_gets_reply_instead_of_waiting(isolated,monkeypatch):
    relay.enqueue([update()],'42');relay.set_state(100,'prepared',prompt='request')
    def missing():raise ValueError('configuration absent')
    monkeypatch.setattr(relay,'Client',missing)
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    relay.process(row,{'chat_id':'42'})
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    assert row['state']=='reply_ready' and row['error']=='agent_unavailable'
