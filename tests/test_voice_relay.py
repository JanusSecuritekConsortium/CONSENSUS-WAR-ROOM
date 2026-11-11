import json
import sqlite3
import pytest
from integrations.msty.personal import voice_relay as relay


@pytest.fixture
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(relay.store,'ROOT',tmp_path)
    monkeypatch.setattr(relay,'launch_token_form',lambda:pytest.fail('tests never open the real token form'))


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
    assert 'request_clarification' in prompt and 'default account from your instructions' in prompt
    assert 'check every account only when asked' in prompt


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
    health=json.loads((relay.store.ROOT/'voice-relay-health.json').read_text(encoding='utf-8'))
    assert health['telegram_receiver'] is True and health['msty_ready'] is False
    assert health['msty_failure']=='unreachable' and health['msty_checked_at']

def test_msty_outage_alerts_once_and_reports_recovery(isolated,monkeypatch):
    sent=[];monkeypatch.setattr(relay,'api',lambda route,method,data:sent.append(data['text']))
    route={'chat_id':'42'}
    for failures in range(1,relay.MSTY_ALERT_AFTER):relay.msty_alert(route,False,failures,'unreachable')
    assert sent==[]
    relay.msty_alert(route,False,relay.MSTY_ALERT_AFTER,'unauthorized')
    relay.msty_alert(route,False,relay.MSTY_ALERT_AFTER+1,'unauthorized')
    assert len(sent)==1 and 'token' in sent[0] and 'voice_setup' in sent[0]
    assert 'send them again' in sent[0]  # offline requests are answered with an error, not replayed
    relay.msty_alert(route,True,0,None);relay.msty_alert(route,True,0,None)
    assert len(sent)==2 and 'again' in sent[1]


def test_msty_outage_alert_follows_up_when_server_returns_with_new_token(isolated,monkeypatch):
    sent=[]
    monkeypatch.setattr(relay,'api',lambda route,method,data:sent.append(data['text']))
    route={'chat_id':'42'}
    for reason in ('unreachable','unreachable','unauthorized','unreachable','unauthorized'):
        relay.msty_alert(route,False,relay.MSTY_ALERT_AFTER,reason)
    assert len(sent)==2
    assert 'Built-in Server' in sent[0]
    assert 'token' in sent[1] and 'voice_setup' in sent[1]
    relay.msty_alert(route,True,0,None)
    assert len(sent)==3 and 'again' in sent[2]
    relay.msty_alert(route,False,relay.MSTY_ALERT_AFTER,'unreachable')
    assert len(sent)==4


def test_token_form_opens_once_per_rejected_token(isolated,monkeypatch):
    opened=[];monkeypatch.setattr(relay,'launch_token_form',lambda:opened.append(1))
    monkeypatch.setattr(relay.store,'load',lambda:{})
    relay.token_form(False,'unreachable')
    assert opened==[]  # Msty Go simply not running: nothing to paste yet
    for _ in range(3):relay.token_form(False,'unauthorized')
    relay.token_form(False,'unreachable');relay.token_form(False,'unauthorized')
    assert opened==[1]  # one form for one outage, however long it lasts
    relay.token_form(True,None)
    relay.token_form(False,'unauthorized')
    assert opened==[1,1]  # the next Msty restart gets a fresh form


def test_token_form_can_be_turned_off_and_survives_no_desktop(isolated,monkeypatch):
    monkeypatch.setattr(relay.store,'load',lambda:{'open_token_form':False})
    relay.token_form(False,'unauthorized')  # the fixture fails if it launches
    monkeypatch.setattr(relay.store,'load',lambda:{})
    def no_desktop():raise OSError('no desktop session')
    monkeypatch.setattr(relay,'launch_token_form',no_desktop)
    relay.token_form(False,'unauthorized')
    assert not (relay.store.ROOT/'msty-token-form.json').exists()  # retried at the next check


def test_token_form_keeps_the_saved_address(monkeypatch):
    pytest.importorskip('tkinter')
    from integrations.msty.personal import voice_setup
    monkeypatch.setattr(voice_setup.store,'secret_read',lambda name:{'url':'http://127.0.0.1:7000/mcp','token':'x'})
    assert voice_setup.saved_url()=='http://127.0.0.1:7000/mcp'
    def missing(name):raise ImportError('no win32crypt')
    monkeypatch.setattr(voice_setup.store,'secret_read',missing)
    assert voice_setup.saved_url()==voice_setup.DEFAULT_URL


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


def _delivered(monkeypatch, decoded, reply='Tienes dos citas mañana.', error=None):
    message=update()['message'];message.pop('text');message['voice']={'file_id':'f'}
    with relay.database() as db:
        db.execute('INSERT INTO inbox (update_id,message,state,reply,error,created_at,decoded,language) VALUES (?,?,?,?,?,?,?,?)',
                   (100,json.dumps(message),'reply_ready',reply,error,'2026-10-30T00:00:00+00:00',
                    json.dumps(decoded) if decoded else None,'es'))
    monkeypatch.setattr(relay,'api',lambda route,method,data:{'chat':{'id':42},'message_id':9})
    monkeypatch.setattr('integrations.msty.personal.telegram_buttons.make',lambda *a,**k:None)
    monkeypatch.setattr(relay.interactions,'bind',lambda *a:None)
    started=[]
    monkeypatch.setattr(relay,'start',lambda target,*args:started.append(args))
    with relay.database() as db:row=dict(db.execute('SELECT * FROM inbox').fetchone())
    relay.process(row,{'chat_id':'42'})
    return started


def test_voice_note_gets_a_spoken_reply_after_the_text(isolated,monkeypatch):
    started=_delivered(monkeypatch,{'status':'transcribed','text':'¿Qué tengo mañana?','forwarded':False})
    assert started==[(100,{'chat_id':'42'},'Tienes dos citas mañana.','es',7)]
    with relay.database() as db:assert db.execute('SELECT state FROM inbox').fetchone()[0]=='delivered'


def test_text_forwards_errors_and_long_answers_stay_text_only(isolated,monkeypatch):
    assert _delivered(monkeypatch,None)==[]
    with relay.database() as db:db.execute('DELETE FROM inbox')
    assert _delivered(monkeypatch,{'status':'transcribed','text':'x','forwarded':True})==[]
    with relay.database() as db:db.execute('DELETE FROM inbox')
    assert _delivered(monkeypatch,{'status':'transcribed','text':'x','forwarded':False},error='agent_unavailable')==[]
    with relay.database() as db:db.execute('DELETE FROM inbox')
    assert _delivered(monkeypatch,{'status':'transcribed','text':'x','forwarded':False},reply='a'*2000)==[]


def test_failed_voice_reply_is_recorded_not_resent(isolated,monkeypatch):
    from contextlib import contextmanager
    from integrations.msty.personal import spoken_briefing
    relay.enqueue([update()],'42');relay.set_state(100,'delivered')
    @contextmanager
    def broken(text,lang):raise RuntimeError('no voice')
    sent=[]
    monkeypatch.setattr(spoken_briefing,'audio_file',broken)
    monkeypatch.setattr(spoken_briefing,'send_voice',lambda *a,**k:sent.append(a))
    relay.spoken_reply(100,{'chat_id':'42'},'Hola','es',7)
    with relay.database() as db:row=db.execute('SELECT state,error FROM inbox').fetchone()
    assert tuple(row)==('delivered','voice_reply_failed:RuntimeError') and sent==[]
