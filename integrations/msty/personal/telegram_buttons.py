"""Inline Telegram controls backed by private, message-bound opaque tokens."""
from . import interaction_store as state
from .language import choose


def make(route, *, lang='en', text=None, items=(), choice=False, briefing=False):
    rows = []
    if choice:
        rows.append([(choose(lang, 'Read aloud', 'Leer en voz alta'), 'choice', {'value': '1'}),
                     (choose(lang, 'Text', 'Texto'), 'choice', {'value': '2'})])
    elif text:
        rows.append([(choose(lang, 'Read aloud', 'Leer en voz alta'),
                      'choice' if briefing else 'read', {'value': '1'} if briefing else {'text': text, 'lang': lang})])
    rows.append([(choose(lang, 'What’s next?', '¿Qué sigue?'), 'next', {}),
                 (choose(lang, 'Where?', '¿Dónde?'), 'where', {}),
                 (choose(lang, 'Follow-ups', 'Seguimientos'), 'followups', {})])
    for index, item in enumerate(items[:8], 1):
        rows.append([(str(index)+' · '+choose(lang, 'Handled', 'Hecho'), 'handled', {'id': item['id']}),
                     (str(index)+' · '+choose(lang, 'Tomorrow', 'Mañana'), 'tomorrow', {'id': item['id']})])
    return state.keyboard(route, rows)


def for_receipt(receipt, route, body):
    return make(route, lang=receipt.get('language', 'en'), text=body,
                choice=receipt.get('choice_offer', False), briefing=True)
