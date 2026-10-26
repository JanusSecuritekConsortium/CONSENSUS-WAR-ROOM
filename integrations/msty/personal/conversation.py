"""One local command router for authenticated text, voice and button input."""
from datetime import datetime, timezone
import json
from . import interaction_store as state
from .language import choose


def answer(message, route, lang, request_key, *, callback=None):
    from . import agenda_query, followups, spoken_briefing as spoken
    action, payload = callback or (None, {})
    if action == 'read':
        # A durable voice receipt makes repeated updates and upload uncertainty
        # use the same no-resend protection as scheduled briefing narration.
        path = spoken.publication.VAULT/'Deliveries'/('conversation-voice-'+str(abs(message['message_id']))+'.json')
        if not path.exists():
            receipt = {'status': 'awaiting_choice', 'target_hash': state.owner(route),
                       'choice_message_id': message.get('reply_to_message', {}).get('message_id'),
                       'offered_at': datetime.now(timezone.utc).isoformat(), 'message_ids': [],
                       'telegram_text': payload['text'], 'language': payload.get('lang', lang)}
            spoken.save(path, receipt)
        message = {**message, 'text': '1'}
    elif action == 'choice':
        message = {**message, 'text': payload['value']}
    elif action in ('next', 'where', 'followups'):
        message = {**message, 'text': {'next': 'What is next?', 'where': 'Where is my next meeting?',
                                     'followups': 'follow-ups'}[action]}
    control = followups.answer(message, route, lang, request_key, callback=callback)
    if control is not None:
        return control
    choice = spoken.handle_choice(message, route, lang=lang)
    if choice is not None:
        return {'text': choice, 'items': []}
    agenda = agenda_query.answer(message.get('text', ''), lang=lang, route=route)
    return {'text': agenda, 'items': []} if agenda is not None else None
