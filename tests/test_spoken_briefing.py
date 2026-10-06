import json
from datetime import datetime, timezone
from contextlib import contextmanager
import pytest
from integrations.msty.personal import spoken_briefing as s

@pytest.fixture
def setup(tmp_path, monkeypatch):
    route={'chat_id':'42'}
    path=tmp_path/'Deliveries'/'test.json'
    receipt={'status':'prepared','telegram_text':'Monday 09:00: Project review. Possible conflict.', 'message_ids':[]}
    calls=[]
    def call(route, method, data):
        calls.append(data)
        return {'chat':{'id':42},'message_id':100+len(calls)}
    monkeypatch.setattr(s.publication,'telegram_call',call)
    s.offer(receipt,path,route,'morning')
    message={'message_id':201,'text':'2','from':{'id':42},'chat':{'id':42,'type':'private'}}
    return tmp_path,path,route,message,calls

def test_text_exact_and_replay(setup):
    vault,path,route,message,calls=setup
    assert s.handle_choice(message,route,vault=vault)==''
    assert calls[-1]['text']=='Monday 09:00: Project review. Possible conflict.'
    assert s.handle_choice(message,route,vault=vault)==''
    assert len(calls)==2

def test_offer_idempotent(setup):
    vault,path,route,message,calls=setup
    s.offer(json.loads(path.read_text()),path,route,'morning')
    assert len(calls)==1

def test_voice_and_timeout_no_repeat(setup,monkeypatch):
    vault,path,route,message,calls=setup
    message['text']='1'
    @contextmanager
    def audio(text): yield vault/'fake.ogg'
    monkeypatch.setattr(s,'audio_file',audio)
    uploads=[]
    def send(*args):
        uploads.append(1)
        raise TimeoutError()
    monkeypatch.setattr(s,'send_voice',send)
    assert 'unconfirmed' in s.handle_choice(message,route,vault=vault)
    assert 'unconfirmed' in s.handle_choice(message,route,vault=vault)
    assert len(uploads)==1 and len(calls)==1

def test_voice_success(setup,monkeypatch):
    vault,path,route,message,calls=setup
    message['text']='1'
    @contextmanager
    def audio(text):
        assert 'Possible conflict' in text
        yield vault/'fake.ogg'
    monkeypatch.setattr(s,'audio_file',audio)
    monkeypatch.setattr(s,'send_voice',lambda *a:{'message_id':99})
    assert s.handle_choice(message,route,vault=vault)==''
    assert json.loads(path.read_text())['delivery_format']=='voice'
    assert len(calls)==1

def test_render_failure_safe_fallback(setup,monkeypatch):
    vault,path,route,message,calls=setup
    message['text']='1'
    def fail(*a):raise RuntimeError()
    monkeypatch.setattr(s,'audio_file',fail)
    assert s.handle_choice(message,route,vault=vault)==''
    assert len(calls)==2
    assert json.loads(path.read_text())['voice_error']=='local_narration_failed'

def test_expiry_wrong_reply_and_forwarded(setup):
    vault,path,route,message,calls=setup
    message['forward_origin']={'type':'user'}
    assert s.handle_choice(message,route,vault=vault) is None
    del message['forward_origin']
    message['reply_to_message']={'message_id':999}
    assert 'Reply directly' in s.handle_choice(message,route,vault=vault)
    del message['reply_to_message']
    receipt=json.loads(path.read_text());receipt['offered_at']='2020-01-01T00:00:00+00:00'
    s.save(path,receipt)
    assert 'expire' in s.handle_choice(message,route,vault=vault)
    assert len(calls)==1

def test_narration_preserves_qualifiers():
    assert s.narration('- Possible conflict at 09:00. https://example.com/a')=='Possible conflict at 09:00.'
