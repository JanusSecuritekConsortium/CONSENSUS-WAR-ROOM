"""Specific user-controlled reminder overlays; never modify mail or calendars."""
from datetime import datetime
import json
import re
from . import interaction_store as state
from .context import clean, mail_context
from .connectors import TZ
from .language import choose, fold


def task_item(task):
    if isinstance(task, str):
        title = clean(task)
        identity = title.casefold()
    elif isinstance(task, dict):
        if str(task.get('status', 'open')).casefold() in ('done', 'completed', 'cancelled', 'closed'):
            return None
        title = clean(task.get('title') or task.get('text') or task.get('description') or '')
        identity = str(task.get('id') or title.casefold())
    else:
        return None
    return {'id': state.item_id('task', identity), 'title': title, 'kind': 'task'} if title else None


def mail_item(source, message):
    identity = message.get('message_id') or message.get('id')
    if not identity:
        identity = json.dumps([message.get(k) for k in ('date', 'from', 'subject')])
    return {'id': state.item_id('mail', source['id']+'\0'+identity),
            'title': clean(message.get('subject') or '(no subject)'), 'kind': 'mail'}


def items(results, tasks, now):
    found = [item for task in tasks or [] if (item := task_item(task))]
    for source in results:
        if source.get('status') == 'ok':
            found.extend(mail_item(source, candidate['message'])
                         for candidate in mail_context(source.get('messages', []), now)[0])
    found = list({item['id']: item for item in found}.values())
    state.register(found, now)
    return [item for item in found if state.visible(item['id'], now)]


def latest(vault, route, now):
    receipts = []
    for path in (vault/'Deliveries').glob('*.json'):
        try:
            receipt = json.loads(path.read_text(encoding='utf-8'))
            if (receipt.get('target_hash') == state.owner(route) and 'followups' in receipt
                    and receipt.get('status') in ('delivered', 'awaiting_choice', 'selected')):
                receipts.append(receipt)
        except (ValueError, OSError):
            continue
    receipt = max(receipts, key=lambda r: r['generated_at']) if receipts else None
    return [item for item in receipt.get('followups', []) if state.visible(item['id'], now)] if receipt else []


def selection(items, lang, action=None):
    if not items:
        return {'text': choose(lang, 'No available follow-ups in the latest briefing.',
                               'No hay seguimientos disponibles en el último informe.'), 'items': []}
    visible = items[:8]
    text = choose(lang, 'Which follow-up? Choose a button or reply “handled 1” / “tomorrow 1”.',
                        '¿Qué seguimiento? Elige un botón o responde «hecho 1» / «mañana 1».')
    text += '\n'+'\n'.join(str(index)+'. '+item['title'][:160] for index, item in enumerate(visible, 1))
    if len(items) > len(visible):
        text += choose(lang, '\nMore items are available in the briefing.', '\nHay más elementos en el informe.')
    return {'text': text, 'items': visible, 'action': action}


def answer(message, route, lang, request_key, *, now=None, vault=None, callback=None):
    from .publication import VAULT
    now = now or datetime.now(TZ)
    vault = vault or VAULT
    if callback and callback[0] in ('handled', 'tomorrow'):
        return {'text': state.mutate(callback[1]['id'], callback[0], request_key, now, lang), 'items': []}
    text = fold(message.get('text', '')).strip(' .!?¿¡')
    if text in ('follow-ups', 'follow ups', 'show follow-ups', 'seguimientos', 'muestra mis seguimientos'):
        return selection(latest(vault, route, now), lang)
    action = None
    index = None
    match = re.fullmatch(r'(handled|done|tomorrow|hecho|manana)\s+(\d+)', text)
    if match:
        action = 'tomorrow' if match[1] in ('tomorrow', 'manana') else 'handled'
        index = int(match[2])-1
    elif text in ("i've handled this", 'i have handled this', 'handled this', 'done', 'ya esta hecho',
                  'hecho', 'ya lo he hecho', 'me he encargado', 'ya me he encargado de esto'):
        action = 'handled'
    elif text in ('remind me tomorrow', 'remind me about this tomorrow', 'recuerdamelo manana', 'recuerdame manana'):
        action = 'tomorrow'
    if not action:
        return None
    reply_id = message.get('reply_to_message', {}).get('message_id')
    bound = state.selected(route, reply_id) if reply_id else []
    candidates = latest(vault, route, now)
    # Reply-bound IDs remain usable even after a previous idempotent mutation.
    if bound and (index is not None or len(bound) == 1):
        position = index if index is not None else 0
        if 0 <= position < len(bound):
            return {'text': state.mutate(bound[position], action, request_key, now, lang), 'items': []}
    if index is not None:
        return {'text': choose(lang, 'Reply to the follow-up list so that number identifies a specific item.',
                               'Responde a la lista de seguimientos para que el número identifique un elemento concreto.'), 'items': []}
    return selection(candidates, lang, action)
