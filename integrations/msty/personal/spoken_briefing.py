"""Local narration and durable Telegram briefing format selection."""
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from . import publication, store


def narration(text):
    # Keep facts and qualifiers verbatim; URLs are useful in text, not speech.
    text = re.sub(r'https?://\S+', '', text)
    return re.sub(r'(?m)^\s*[-•#]+\s*', '', text).strip()


@contextmanager
def audio_file(text):
    from voice.aurelius_adapter import AureliusAdapter
    from voice.voice_profiles import get_voice_profile
    store.ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='narration-', dir=store.ROOT) as folder:
        profile = get_voice_profile('AURELIUS')
        profile = replace(profile, settings={**profile.settings, 'output_dir': folder})
        with redirect_stdout(io.StringIO()):
            result = AureliusAdapter(profile=profile).save_only(narration(text))
        if not result.ok or not result.audio_path:
            raise RuntimeError('Local Aurelius narration unavailable')
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise RuntimeError('Local audio encoder unavailable')
        output = Path(folder)/'briefing.ogg'
        subprocess.run([ffmpeg, '-nostdin', '-y', '-i', result.audio_path,
                        '-vn', '-ac', '1', '-c:a', 'libopus', '-b:a', '32k', str(output)],
                       check=True, capture_output=True, timeout=120,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if not output.exists() or output.stat().st_size > 49_000_000:
            raise RuntimeError('Narration exceeds delivery limit')
        yield output


def send_voice(route, path):
    import requests
    try:
        with path.open('rb') as stream:
            response = requests.post('https://api.telegram.org/bot'+route['token']+'/sendVoice',
                data={'chat_id': route['chat_id'], 'caption': 'Aurelius briefing'},
                files={'voice': ('briefing.ogg', stream, 'audio/ogg')},
                timeout=(10, 120), allow_redirects=False)
        response.raise_for_status()
        payload = response.json()
        if not payload.get('ok'):
            raise ValueError()
        result = payload['result']
        if str(result['chat']['id']) != str(route['chat_id']) or not result.get('message_id'):
            raise ValueError()
        return result
    except Exception:
        raise RuntimeError('Voice delivery unconfirmed; automatic resend withheld') from None


def save(path, receipt):
    publication.atomic(path, json.dumps(receipt, ensure_ascii=False, indent=2))


def offer(receipt, path, route, mode):
    if receipt.get('status') in ('awaiting_choice', 'selected'):
        return
    prompt_path = path.with_suffix('.choice.json')
    prompt = json.loads(prompt_path.read_text(encoding='utf-8')) if prompt_path.exists() else {}
    title = 'Morning agenda and follow-ups' if mode == 'morning' else 'Evening news' if mode == 'evening' else 'Weekly briefing'
    publication.deliver(title+' is ready. Reply to this message: 1 for voice, 2 for text. Choice expires in 18 hours.',
                        prompt, prompt_path, route)
    receipt.update(status='awaiting_choice', choice_message_id=prompt['message_ids'][0],
                   target_hash=prompt['target_hash'], offered_at=prompt['acknowledged_at'])
    save(path, receipt)


def handle_choice(message, route, *, vault=None):
    """Return None for ordinary messages; otherwise a local delivery outcome."""
    choice = message.get('text', '').strip().casefold().rstrip('.!')
    if choice in ('read it aloud', 'read this aloud', 'read it out loud', 'read this out loud',
                  'send voice', 'voice', 'read the briefing aloud', 'léelo en voz alta',
                  'lee esto en voz alta', 'leelo en voz alta'):
        choice = '1'
    if choice not in ('1', '2'):
        return None
    if (message.get('forward_origin') or message.get('forward_from') or
            str(message.get('from', {}).get('id')) != str(route['chat_id']) or
            message.get('from', {}).get('is_bot') or
            str(message.get('chat', {}).get('id')) != str(route['chat_id']) or
            message.get('chat', {}).get('type') != 'private'):
        return None
    vault = vault or publication.VAULT
    target = hashlib.sha256(str(route['chat_id']).encode()).hexdigest()
    with publication.publication_lock(vault):
        candidates = []
        reply_id = message.get('reply_to_message', {}).get('message_id')
        for path in (vault/'Deliveries').glob('*.json'):
            if path.name.endswith('.choice.json'):
                continue
            try:
                receipt = json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                continue
            if receipt.get('target_hash') != target:
                continue
            if receipt.get('choice_update_message') == message['message_id']:
                if receipt['status'] in ('sending', 'uncertain'):
                    return 'Delivery is unconfirmed. Please check Telegram before requesting another copy.'
                if receipt['status'] == 'delivered':
                    return ''  # Crash after acknowledgement: do not send twice.
            # An explicit reply to a previously delivered digest can request narration.
            if choice == '1' and receipt.get('status') == 'delivered' and reply_id in receipt.get('message_ids', []):
                replay_path = path.with_name(path.stem+'-voice-'+str(message['message_id'])+'.json')
                if replay_path.exists():
                    continue  # Its durable receipt is evaluated in this same scan.
                receipt = {**receipt, 'status':'awaiting_choice', 'message_ids':[],
                           'choice_message_id':reply_id, 'offered_at':datetime.now(timezone.utc).isoformat()}
                receipt.pop('choice_update_message', None)
                path = replay_path
            if receipt.get('status') not in ('awaiting_choice', 'selected'):
                continue
            if reply_id and receipt.get('choice_message_id') != reply_id:
                continue
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(receipt['offered_at'])).total_seconds()
            if age > 18*3600:
                continue
            candidates.append((path, receipt))
        if not reply_id and candidates:
            candidates = [max(candidates, key=lambda item:item[1]['offered_at'])]
        if len(candidates) != 1:
            return 'Reply directly to a current briefing offer: 1 for voice or 2 for text. Old offers expire after 18 hours.'
        path, receipt = candidates[0]
        if receipt.get('status') != 'selected':
            receipt.update(status='selected', choice_update_message=message['message_id'], selected_format=choice)
            save(path, receipt)
        if receipt['selected_format'] == '2':
            publication.deliver(receipt['telegram_text'], receipt, path, route)
            return ''
        try:
            with audio_file(receipt['telegram_text']) as audio:
                receipt.update(status='sending', delivery_format='voice')
                save(path, receipt)
                result = send_voice(route, audio)
                receipt.update(status='delivered', message_ids=[result['message_id']],
                               acknowledged_at=datetime.now(timezone.utc).isoformat())
                save(path, receipt)
        except Exception:
            if receipt['status'] in ('sending', 'delivered'):
                receipt['status'] = 'uncertain'
                save(path, receipt)
                return 'Voice delivery is unconfirmed. Please check Telegram before requesting another copy.'
            # Rendering failed before any upload; exactly one text fallback is safe.
            receipt['voice_error'] = 'local_narration_failed'
            publication.deliver(receipt['telegram_text'], receipt, path, route)
        return ''
