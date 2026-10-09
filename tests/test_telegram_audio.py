import pytest
from unittest.mock import Mock
from integrations.msty.personal import telegram_audio as audio


def message(**extra):
    return {'chat':{'id':42,'type':'private'},'from':{'id':42,'is_bot':False},
            'message_id':7,'voice':{'file_id':'test-file','duration':4,'file_size':20},**extra}


def test_accepts_only_private_owner():
    assert audio.attachment(message(),'42')['request_key']=='telegram:42:7'
    for changed in ({'chat':{'id':1,'type':'group'}},{'from':{'id':12}},
                    {'from':{'id':42,'is_bot':True}}):
        with pytest.raises(ValueError):audio.attachment(message(**changed),'42')


def test_limits_and_non_audio_documents():
    with pytest.raises(ValueError):
        audio.attachment(message(voice={'file_id':'x','duration':601}),'42')
    m=message();del m['voice'];m['document']={'file_id':'x','mime_type':'application/pdf'}
    assert audio.attachment(m,'42') is None


def test_forwarded_audio_is_identified():
    assert audio.attachment(message(forward_origin={'type':'user'}),'42')['forwarded']


def test_rejects_remote_traversal_and_hides_credentials(tmp_path,monkeypatch):
    monkeypatch.setattr(audio.store,'ROOT',tmp_path)
    client=Mock()
    client.post.return_value.json.return_value={'ok':True,'result':{'file_path':'../secret.ogg'}}
    with pytest.raises(RuntimeError,match='^Telegram audio download failed$'):
        audio.download({'token':'SECRET'},audio.attachment(message(),'42'),client)
    client.get.assert_not_called()


def test_removes_partial_oversized_download(tmp_path,monkeypatch):
    item=audio.attachment(message(),'42')
    monkeypatch.setattr(audio.store,'ROOT',tmp_path)
    monkeypatch.setattr(audio,'MAX_BYTES',5)
    client=Mock()
    client.post.return_value.json.return_value={'ok':True,'result':{'file_path':'voice/file.oga'}}
    response=Mock(status_code=200)
    response.iter_content.return_value=[b'123',b'456']
    context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
    client.get.return_value=context
    with pytest.raises(RuntimeError):audio.download({'token':'SECRET'},item,client)
    assert not list((tmp_path/'audio').iterdir())
