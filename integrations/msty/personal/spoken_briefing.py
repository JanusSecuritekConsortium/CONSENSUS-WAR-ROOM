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
from voice.text_normalization import number_to_words, prepare_speech_text
from .language import choose


_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
           'July', 'August', 'September', 'October', 'November', 'December')
_ORDINALS = ('', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth',
             'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth',
             'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth',
             'eighteenth', 'nineteenth', 'twentieth')


def _spoken_timestamp(match):
    day, month = int(match['day']), int(match['month'])
    year = int(match['year']) if match['year'] else 2000
    hour, minute = int(match['hour']), int(match['minute'])
    try:
        datetime(year, month, day, hour, minute)
    except ValueError:
        return match.group(0)  # Do not invent a correction to an invalid timestamp.
    ordinal = _ORDINALS[day] if day <= 20 else (
        'thirtieth' if day == 30 else ('twenty ' if day < 30 else 'thirty ')+_ORDINALS[day % 10])
    date = 'the '+ordinal+' of '+_MONTHS[month-1]
    if match['year']:
        date += ' '+number_to_words(year)
    time = number_to_words(hour)+' '+(
        "o'clock" if minute == 0 else 'oh '+number_to_words(minute) if minute < 10 else number_to_words(minute))
    return date+' at '+time


# Standing notes that stay in the text reply but are not read aloud: they repeat on every agenda
# and carry no news. Real overlap warnings and missing-title notices are still spoken.
FINE_PRINT = (
    'No overlaps detected among the appointments included in this reminder.',
    'No se detectaron solapamientos entre las citas de este recordatorio.',
    'No overlaps detected between events with known start and end times.',
    'No se detectaron solapamientos entre eventos con horas de inicio y fin conocidas.',
    'Events without an end time, all-day events and events marked as available are excluded from conflict checks. Calendar entries do not confirm attendance.',
    'Los eventos sin hora de fin, de todo el día o marcados como disponibles no se comprueban para solapamientos. Las citas no confirman asistencia.',
    'Calendar source may lag updates or have limited coverage.',
    'La fuente del calendario puede tardar en actualizarse o tener cobertura limitada.',
)


def narration(text, lang='en'):
    text = chr(10).join(line for line in str(text).splitlines() if line.strip() not in FINE_PRINT)
    # The agenda heading's timezone and whole-day window are for reading, not listening.
    text = re.sub(r'\s*·\s*Europe/Madrid\b', '', text)
    text = re.sub(r'\s*·\s*00:00[–-]24:00(?=\s*(?:·|$))', '', text, flags=re.MULTILINE)
    # Each appointment line ends with its calendar's name in brackets: useful to read, noise to hear.
    # The calendar is named once, before the first appointment, instead of after every one.
    calendars = []

    def _without_calendar(match):
        if match['calendar'] not in calendars:
            calendars.append(match['calendar'])
        return match['line']
    text = re.sub(r'^(?P<line>\s*- (?:\d{2}:\d{2}|All day|Todo el día)\b.*?)[ \t]*\[(?P<calendar>[^\[\]\n]+)\][ \t]*$',
                  _without_calendar, text, flags=re.MULTILINE)
    if calendars:
        names = (' y ' if lang == 'es' else ' and ').join(calendars)
        intro = ('En '+names+' tienes las siguientes citas:' if lang == 'es' else
                 'On '+names+' you have the following appointments:')
        text = re.sub(r'^(?=\s*- (?:\d{2}:\d{2}|All day|Todo el día)\b)', intro+chr(10), text, count=1, flags=re.MULTILINE)
    # Keep facts and qualifiers verbatim; URLs are useful in text, not speech.
    text = re.sub(r'\[([^\]\n]+)\]\(https?://[^\s)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    # The digest publisher explicitly emits day/month, not US month/day.
    text = re.sub(r'(?<![\w/])(?P<day>\d{1,2})/(?P<month>\d{1,2})'
                  r'(?:/(?P<year>\d{4}))?\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})(?!\d)',
                  _spoken_timestamp if lang == 'en' else _spanish_timestamp, text)
    text = re.sub(r'(?<![\w/])(?P<day>\d{2})/(?P<month>\d{2})(?:/(?P<year>\d{4}))?(?![\w/])',
                  lambda match: _spoken_date(match, lang), text)
    return prepare_speech_text(text, lang=lang)


def _spoken_date(match, lang):
    values = {**match.groupdict(), 'hour': '0', 'minute': '00'}
    try:
        datetime(int(values['year'] or 2000), int(values['month']), int(values['day']))
    except ValueError:
        return match.group(0)
    return (_spanish_timestamp(values).split(' a las ')[0] if lang == 'es' else
            _spoken_timestamp(values).split(' at ')[0])


def _spanish_timestamp(match):
    day, month = int(match['day']), int(match['month'])
    try:
        datetime(int(match['year'] or 2000), month, day, int(match['hour']), int(match['minute']))
    except ValueError:
        return match.group(0)
    months = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
              'septiembre', 'octubre', 'noviembre', 'diciembre')
    return str(day)+' de '+months[month-1]+(' de '+match['year'] if match['year'] else '')+' a las '+match['hour']+':'+match['minute']


def spanish_settings(settings, sapi_voices=None):
    """AURELIUS's settings for Spanish speech; English settings are left as they are.

    A Spanish male voice (Pablo, a OneCore voice SAPI cannot list) is reshaped more gently than English,
    because the voice model was trained on English speech. Installed SAPI Spanish voices are the fallback."""
    if sapi_voices is None:
        from voice.tts_backends import list_sapi_voices
        sapi_voices = list_sapi_voices()
    spanish = dict(settings.get('spanish') or {})
    names = [str(name) for name in spanish.pop('base_voice_name', [])]
    names += [voice['name'] for voice in sapi_voices if voice.get('language', '').startswith('es')]
    if not names:
        raise RuntimeError('Local Spanish voice unavailable')
    return {**settings, 'base_voice_gender': '', **spanish, 'base_voice_name': names,
            'base_voice_language': 'es', 'speech_language': 'es'}


def installed_voices(language_code):
    """Names of the Windows (OneCore) voices for one language, e.g. '403' for Catalan; [] off Windows."""
    try:
        import winreg
        root = r'SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens'
        names = []
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root) as tokens:
            for index in range(winreg.QueryInfoKey(tokens)[0]):
                with winreg.OpenKey(tokens, winreg.EnumKey(tokens, index)+r'\Attributes') as attributes:
                    if str(winreg.QueryValueEx(attributes, 'Language')[0]).lower() == language_code:
                        names.append(str(winreg.QueryValueEx(attributes, 'Name')[0]))
        return names
    except (ImportError, OSError):
        return []


def catalan_settings(settings, voices=None):
    """AURELIUS's settings for Catalan titles, from an installed Catalan Windows voice (Windows' language
    settings add one). Without it Catalan is read in Spanish."""
    names = installed_voices('403') if voices is None else list(voices)
    if not names:
        raise RuntimeError('Local Catalan voice unavailable')
    catalan = {key: value for key, value in dict(settings.get('catalan') or {}).items() if key != 'base_voice_name'}
    return {**settings, 'base_voice_gender': '', **catalan, 'base_voice_name': names,
            'base_voice_language': 'ca', 'speech_language': 'ca'}


@contextmanager
def audio_file(text, lang='en'):
    from voice.aurelius_adapter import AureliusAdapter
    from voice.voice_profiles import get_voice_profile
    store.ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='narration-', dir=store.ROOT) as folder:
        from .title_language import merge, segments
        profile = get_voice_profile('AURELIUS')
        voices = {'en': profile.settings}
        voices[lang] = spanish_settings(profile.settings) if lang == 'es' else profile.settings
        wavs = []
        # Calendar titles in another language are read in that language's voice; the rest keeps the reply's.
        parts = segments(narration(text, lang), lang)
        if any(part_lang == 'ca' for _, part_lang in parts):
            try:
                voices['ca'] = catalan_settings(profile.settings)
            except RuntimeError:  # no Catalan voice yet: Catalan joins the Spanish parts
                parts = merge([(part, 'es' if part_lang == 'ca' else part_lang) for part, part_lang in parts])
        for index, (part, part_lang) in enumerate(parts):
            if part_lang not in voices:
                try:
                    voices[part_lang] = spanish_settings(profile.settings)
                except RuntimeError:
                    voices[part_lang] = voices[lang]
            settings = {**voices[part_lang], 'output_dir': str(Path(folder)/f'part{index}')}
            with redirect_stdout(io.StringIO()):
                result = AureliusAdapter(profile=replace(profile, settings=settings)).save_only(part)
            if not result.ok or not result.audio_path:
                raise RuntimeError('Local Aurelius narration unavailable')
            wavs.append(result.audio_path)
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise RuntimeError('Local audio encoder unavailable')
        output = Path(folder)/'briefing.ogg'
        inputs = [argument for wav in wavs for argument in ('-i', wav)]
        joined = ''.join(f'[{i}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=mono[a{i}];' for i in range(len(wavs)))
        joined += ''.join(f'[a{i}]' for i in range(len(wavs)))+f'concat=n={len(wavs)}:v=0:a=1[out]'
        subprocess.run([ffmpeg, '-nostdin', '-y', *inputs, '-filter_complex', joined, '-map', '[out]',
                        '-vn', '-ac', '1', '-c:a', 'libopus', '-b:a', '32k', str(output)],
                       check=True, capture_output=True, timeout=120,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if not output.exists() or output.stat().st_size > 49_000_000:
            raise RuntimeError('Narration exceeds delivery limit')
        yield output


def send_voice(route, path, markup=None, reply_to=None, caption='Aurelius'):
    import requests
    try:
        with path.open('rb') as stream:
            data = {'chat_id': route['chat_id'], 'caption': caption}
            if markup:
                data['reply_markup'] = json.dumps(markup)
            if reply_to:
                data['reply_parameters'] = json.dumps({'message_id': reply_to, 'allow_sending_without_reply': True})
            response = requests.post('https://api.telegram.org/bot'+route['token']+'/sendVoice',
                data=data,
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
    prompt.update(interactive=True, choice_offer=True)
    title = 'Morning agenda and follow-ups' if mode == 'morning' else 'Evening news' if mode == 'evening' else 'Weekly briefing'
    publication.deliver(title+' is ready. Reply to this message: 1 for voice, 2 for text. Choice expires in 18 hours.',
                        prompt, prompt_path, route)
    receipt.update(status='awaiting_choice', choice_message_id=prompt['message_ids'][0],
                   target_hash=prompt['target_hash'], offered_at=prompt['acknowledged_at'])
    save(path, receipt)


def handle_choice(message, route, *, vault=None, lang='en'):
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
                    return choose(lang, 'Delivery is unconfirmed. Please check Telegram before requesting another copy.', 'La entrega no está confirmada. Comprueba Telegram antes de pedir otra copia.')
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
                receipt.pop('reply_markup', None)
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
            return choose(lang, 'Reply directly to a current briefing offer: 1 for voice or 2 for text. Old offers expire after 18 hours.', 'Responde a una oferta actual del informe: 1 para voz o 2 para texto. Las ofertas caducan a las 18 horas.')
        path, receipt = candidates[0]
        if receipt.get('status') != 'selected':
            receipt.update(status='selected', choice_update_message=message['message_id'], selected_format=choice)
            save(path, receipt)
        if receipt['selected_format'] == '2':
            receipt.pop('reply_markup', None)  # A voice replay must not reuse old bindings.
            publication.deliver(receipt['telegram_text'], receipt, path, route)
            return ''
        try:
            rendering = audio_file(receipt['telegram_text'], lang='es') if receipt.get('language') == 'es' else audio_file(receipt['telegram_text'])
            with rendering as audio:
                from .telegram_buttons import make
                from .interaction_store import bind
                markup = make(route, lang=receipt.get('language', 'en')) if receipt.get('interactive') else None
                receipt.update(status='sending', delivery_format='voice')
                save(path, receipt)
                result = send_voice(route, audio, markup)
                if markup:
                    bind(route, markup, result['message_id'], [item['id'] for item in receipt.get('followups', [])] if len(receipt.get('followups', [])) == 1 else [])
                receipt.update(status='delivered', message_ids=[result['message_id']],
                               acknowledged_at=datetime.now(timezone.utc).isoformat())
                save(path, receipt)
        except Exception:
            if receipt['status'] in ('sending', 'delivered'):
                receipt['status'] = 'uncertain'
                save(path, receipt)
                return choose(lang, 'Voice delivery is unconfirmed. Please check Telegram before requesting another copy.', 'La entrega de voz no está confirmada. Comprueba Telegram antes de pedir otra copia.')
            # Rendering failed before any upload; exactly one text fallback is safe.
            receipt['voice_error'] = 'local_narration_failed'
            publication.deliver(receipt['telegram_text'], receipt, path, route)
        return ''
