"""Which language each calendar title is written in, so speech can read it in the matching voice.

Titles are classified (Spanish, English or Catalan) when the calendar is read and kept in Aurelius's
private folder on this PC.
A title with no clear signal (a name such as "Laura") is read in Spanish; English needs a clear signal.
"""
import json
import re

from . import store
from .language import fold

FILE = 'calendar-title-languages.json'
LIMIT = 500
LANGUAGES = ('en', 'es', 'ca')

_SPANISH = set('''de del la el los las y con para en por al sin sobre reunion cena comida almuerzo desayuno
llamada cita revision dentista cumpleanos clase entrega viaje vuelo visita presupuesto proveedor pedido
firma junta curso examen mercado recoger pagar enviar aceite contrato medico cole colegio partido fiesta
boda entrenamiento gimnasio peluqueria compra recogida seguimiento informe entrevista presentacion
taller plazo equipo semanal mensual tarde manana noche hoy'''.split())
_CATALAN = set('''amb els les i sopar dinar esmorzar reunio trucada aniversari classe lliurament viatge vol pressupost
proveidor comanda signatura curs mercat recollir oli contracte metge escola festa casament entrenament gimnas
perruqueria seguiment presentacio termini equip setmanal mensual tarda mati nit avui dilluns dimarts dimecres
dijous divendres dissabte diumenge setmana feina cosa casa nostra'''.split())
_ENGLISH = set('''the of and with for to at on from about meeting call review lunch dinner breakfast project
appointment dentist birthday class delivery trip flight visit budget supplier order sync standup weekly
monthly check team interview workshop deadline catch up presentation demo webinar training gym haircut
shopping pickup follow report party wedding game practice session kickoff planning retro one'''.split())


def classify(title):
    """'es', 'en', 'ca', or None when the title gives no clear signal."""
    text = str(title or '')
    words = re.findall(r'[a-z]+', fold(text))
    shared = len(re.findall(r'[éíóúÉÍÓÚ]', text))  # accents both Spanish and Catalan use
    scores = {
        'es': sum(word in _SPANISH for word in words) + (2 if re.search(r'[ñÑáÁ¿¡]', text) else 0) + shared,
        'en': sum(word in _ENGLISH for word in words) + len(re.findall(r"\b\w+'s\b", text)),
        'ca': sum(word in _CATALAN for word in words) + (2 if re.search(r'[àèòïüçÀÈÒÏÜÇ·]', text) else 0) + shared,
    }
    best = max(scores.values())
    leaders = [lang for lang, score in scores.items() if score == best]
    return leaders[0] if best and len(leaders) == 1 else None


def known():
    try:
        data = json.loads((store.ROOT/FILE).read_text(encoding='utf-8'))
        return {str(title): lang for title, lang in data.items() if lang in LANGUAGES}
    except (OSError, ValueError, AttributeError):
        return {}


def remember(events):
    """Record the language of each event title; never raises, so the calendar always loads."""
    try:
        titles = dict(known())
        for event in events or []:
            title = re.sub(r'\s+', ' ', str(event.get('title') or '')).strip()
            lang = classify(title) or 'es'  # unsure (a name such as "Laura"): read it in Spanish
            if 3 <= len(title) <= 120:
                titles.pop(title, None)
                titles[title] = lang  # most recent last
        titles = dict(list(titles.items())[-LIMIT:])
        store.ROOT.mkdir(parents=True, exist_ok=True)
        (store.ROOT/FILE).write_text(json.dumps(titles, ensure_ascii=False, indent=0), encoding='utf-8')
    except Exception:
        pass


def segments(text, lang, titles=None):
    """Split speech into (text, language) parts: known titles in the other language get their own part."""
    titles = known() if titles is None else titles
    others = sorted({title for title, title_lang in titles.items() if title_lang != lang and len(title) >= 3},
                    key=len, reverse=True)
    if not others or lang not in LANGUAGES:
        return [(text, lang)]
    pattern = re.compile('|'.join(r'(?<!\w)'+re.escape(title)+r'(?!\w)' for title in others), re.IGNORECASE)
    lookup = {title.casefold(): titles[title] for title in others}
    parts, position = [], 0
    for match in pattern.finditer(text):
        if match.start() > position:
            parts.append((text[position:match.start()], lang))
        parts.append((match.group(0), lookup[match.group(0).casefold()]))
        position = match.end()
    if position < len(text):
        parts.append((text[position:], lang))
    return merge(parts) or [(text, lang)]


def merge(parts):
    """Join neighbouring parts in the same language; punctuation alone joins the previous part."""
    merged = []
    for part, part_lang in parts:
        if not re.search(r'\w', part):
            if merged:
                merged[-1] = (merged[-1][0]+part, merged[-1][1])
            continue
        if merged and merged[-1][1] == part_lang:
            merged[-1] = (merged[-1][0]+part, part_lang)
        else:
            merged.append((part, part_lang))
    return merged
