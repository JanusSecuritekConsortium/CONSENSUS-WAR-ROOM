"""Bounded Telegram audio ingestion. Does not poll or execute user actions."""
import re
from pathlib import Path
import requests
from . import store

MAX_BYTES = 20_000_000
MAX_SECONDS = 600
EXTENSIONS = {'.ogg', '.oga', '.opus', '.mp3', '.wav', '.m4a', '.webm', '.mp4'}


def attachment(message, allowed_chat):
    chat = message.get('chat') or {}
    sender = message.get('from') or {}
    if (chat.get('type') != 'private' or str(chat.get('id')) != str(allowed_chat)
            or str(sender.get('id')) != str(allowed_chat) or sender.get('is_bot')):
        raise ValueError('Audio sender is not the configured private user')
    kind = next((k for k in ('voice', 'audio', 'document') if message.get(k)), None)
    if not kind:
        return None
    item = message[kind]
    if kind == 'document' and not str(item.get('mime_type', '')).startswith('audio/'):
        return None
    if item.get('file_size', 0) > MAX_BYTES or item.get('duration', 0) > MAX_SECONDS:
        raise ValueError('Audio exceeds twenty MB or ten minutes')
    if not isinstance(item.get('file_id'), str) or not item['file_id']:
        raise ValueError('Missing Telegram file ID')
    if not isinstance(message.get('message_id'), int) or message['message_id'] <= 0:
        raise ValueError('Invalid message ID')
    return {'file_id':item['file_id'], 'message_id':message['message_id'], 'kind':kind,
            'forwarded':bool(message.get('forward_origin') or message.get('forward_from')),
            'request_key':f"telegram:{allowed_chat}:{message['message_id']}"}


def download(route, item, session=None):
    client = session or requests.Session()
    folder = store.ROOT / 'audio'
    folder.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        result = client.post('https://api.telegram.org/bot'+route['token']+'/getFile',
            json={'file_id':item['file_id']}, timeout=25, allow_redirects=False)
        result.raise_for_status()
        metadata = result.json()
        if not metadata.get('ok'):
            raise ValueError('File lookup failed')
        remote = metadata['result']['file_path']
        if (not re.fullmatch(r'[A-Za-z0-9_./-]+', remote) or remote.startswith('/')
                or '..' in remote.split('/') or Path(remote).suffix.lower() not in EXTENSIONS
                or metadata['result'].get('file_size', 0) > MAX_BYTES):
            raise ValueError('Invalid audio download metadata')
        # Local names never incorporate Telegram-supplied filenames or directories.
        path = folder / ('telegram-'+str(item['message_id'])+Path(remote).suffix.lower())
        temporary = path.with_suffix(path.suffix+'.part')
        with client.get('https://api.telegram.org/file/bot'+route['token']+'/'+remote,
                        stream=True, timeout=(10, 30), allow_redirects=False) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError('Download did not return a file')
            size = 0
            with temporary.open('wb') as output:
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError('Download too large')
                    output.write(chunk)
            if not size:
                raise ValueError('Empty audio')
        temporary.replace(path)
        return path
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise RuntimeError('Telegram audio download failed') from None
    finally:
        if session is None:
            client.close()


def transcribe_message(message, route):
    from .voice import transcribe
    item = attachment(message, route['chat_id'])
    if item is None:
        return {'status':'unsupported'}
    path = download(route, item)
    try:
        result = transcribe(str(path))
        return dict(result, request_key=item['request_key'], forwarded=item['forwarded'],
                    source='telegram_audio', execution_authorized=False)
    finally:
        path.unlink(missing_ok=True)
