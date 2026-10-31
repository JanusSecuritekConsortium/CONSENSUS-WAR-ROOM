"""Local Msty classification of one changed conversation into validated JSON."""
from __future__ import annotations

from datetime import date, datetime
import json
import math
import re

import requests

from . import sources



class ModelUnavailable(RuntimeError):
    """Msty could not be reached or did not answer; nothing was changed."""


class ModelOutputError(ValueError):
    """The model answered with something that is not a valid classification."""


SCHEMA = {
    'type': 'object',
    'properties': {
        'waiting_on': {'type': 'string', 'enum': ['owner', 'contact', 'none']},
        'needs_reply': {'type': 'boolean'},
        'reply_kind': {'type': 'string', 'enum': ['question', 'request', 'none']},
        'informational': {'type': 'boolean'},
        'urgent': {'type': 'boolean'},
        'confidence': {'type': 'number'},
        'summary': {'type': 'string'},
        'action': {'type': ['string', 'null']},
        'commitments': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'text': {'type': 'string'}, 'due_date': {'type': ['string', 'null']},
            'due_text': {'type': ['string', 'null']}, 'completed': {'type': 'boolean'},
            'confidence': {'type': 'number'}},
            'required': ['text', 'due_date', 'due_text', 'completed', 'confidence']}},
        'appointment': {'type': ['object', 'null'], 'properties': {
            'title': {'type': 'string'}, 'date': {'type': ['string', 'null']}, 'time': {'type': ['string', 'null']},
            'status': {'type': 'string', 'enum': ['proposed', 'confirmed', 'declined']},
            'confidence': {'type': 'number'}},
            'required': ['title', 'date', 'time', 'status', 'confidence']},
    },
    'required': ['waiting_on', 'needs_reply', 'reply_kind', 'informational', 'urgent', 'confidence',
                 'summary', 'action', 'commitments', 'appointment'],
}

SYSTEM = '''You track what needs the attention of {owner}, who owns these email and chat conversations.
Messages are oldest first. Lines starting [OWNER] were written by {owner}; [CONTACT] lines by the other person.
Today is {today} ({weekday}). Answer with JSON only.

- waiting_on: "owner" if the next move belongs to {owner} (a question or request is unanswered), "contact" if {owner} replied or delivered and now waits for the other person, otherwise "none".
- needs_reply: true only for a direct question, explicit request, invitation or confirmation request addressed to {owner} that is still unanswered. Thanks, acknowledgements, emoji, FYI notices, newsletters, receipts and automated mail are false.
- reply_kind: "question" when an answer is wanted, "request" when an action or deliverable is wanted, else "none".
- commitments: only promises made in [OWNER] lines ("I'll send it tomorrow"). text is a short imperative ("Send Paul the PDF"). due_date is YYYY-MM-DD only when the timing is clear; otherwise null and copy the vague timing into due_text. completed is true only if a later message shows it was done.
- appointment: a proposed meeting, call, dinner or event with its date (YYYY-MM-DD) and time (HH:MM) when stated, else null. status proposed, confirmed or declined.
- summary: one short sentence about what matters, naming the person. action: the next step for {owner}, or null.
- confidence: 0 to 1 for the whole classification. Never invent dates, people or promises.'''


def build_prompt(thread: dict, settings: dict, now: datetime) -> list[dict]:
    local = now.astimezone(settings['tz'])
    system = SYSTEM.format(owner=settings['owner_name'], today=local.date().isoformat(), weekday=local.strftime('%A'))
    lines = [f'Channel: {thread["channel"]}', f'Subject: {thread.get("subject") or "(none)"}',
             f'Other person: {thread.get("counterpart_name") or "unknown"}', '']
    count = settings['context_messages'] if thread['channel'] == 'email' else settings.get('chat_context_messages', 15)
    for message in thread['messages'][-count:]:
        who = 'OWNER' if message['direction'] == 'sent' else 'CONTACT'
        stamp = datetime.fromisoformat(message['at']).astimezone(settings['tz']).strftime('%a %Y-%m-%d %H:%M')
        lines.append(f'[{who}] {stamp}: {message["text"]}')
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': '\n'.join(lines)}]


def chat(messages: list[dict], settings: dict, *, schema: dict | None = None, post=requests.post) -> str:
    body = {'model': settings['model'], 'messages': messages, 'stream': False, 'think': False,
            'keep_alive': '30m', 'options': {'temperature': 0}}
    if schema:
        body['format'] = schema
    try:
        response = post(settings['msty_base_url'] + '/api/chat', json=body,
                        timeout=(5, settings['model_timeout_seconds']))
        response.raise_for_status()
        return response.json()['message']['content']
    except (requests.RequestException, KeyError, ValueError, TypeError) as error:
        raise ModelUnavailable(type(error).__name__) from None


def warm(settings: dict, *, post=requests.post) -> None:
    """Load the model once with a generous timeout; a cold load can take several minutes."""
    try:
        post(settings['msty_base_url'] + '/api/generate', json={'model': settings['model'], 'prompt': '', 'keep_alive': '30m'},
             timeout=(5, 900)).raise_for_status()
    except requests.RequestException as error:
        raise ModelUnavailable(type(error).__name__) from None


def classify(thread: dict, settings: dict, now: datetime, *, post=requests.post) -> dict:
    content = chat(build_prompt(thread, settings, now), settings, schema=SCHEMA, post=post)
    return validate(content)


def _bool(value, name):
    if not isinstance(value, bool):
        raise ModelOutputError(f'{name} must be true or false')
    return value


def _confidence(value, name='confidence'):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or math.isnan(value) or not 0 <= value <= 1:
        raise ModelOutputError(f'{name} must be a number from 0 to 1')
    return round(float(value), 3)


def _text(value, name, limit, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        if optional:
            return None
        raise ModelOutputError(f'{name} must be text')
    return ' '.join(value.split())[:limit]


def _date(value):
    if value in (None, ''):
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None  # an unusable date is dropped, never guessed
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _time(value):
    if isinstance(value, str) and re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value.strip()):
        return value.strip()
    return None


def validate(content) -> dict:
    """Deterministic gate between model text and stored state."""
    if isinstance(content, str):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip())
        try:
            data = json.loads(text)
        except ValueError:
            raise ModelOutputError('not JSON') from None
    else:
        data = content
    if not isinstance(data, dict):
        raise ModelOutputError('not an object')
    waiting_on = data.get('waiting_on')
    if waiting_on not in ('owner', 'contact', 'none'):
        raise ModelOutputError('waiting_on is invalid')
    reply_kind = data.get('reply_kind', 'none')
    if reply_kind not in ('question', 'request', 'none'):
        raise ModelOutputError('reply_kind is invalid')
    result = {
        'waiting_on': waiting_on,
        'needs_reply': _bool(data.get('needs_reply'), 'needs_reply'),
        'reply_kind': reply_kind,
        'informational': _bool(data.get('informational', False), 'informational'),
        'urgent': _bool(data.get('urgent', False), 'urgent'),
        'confidence': _confidence(data.get('confidence')),
        'summary': _text(data.get('summary'), 'summary', 200),
        'action': _text(data.get('action'), 'action', 160, optional=True),
        'commitments': [],
        'appointment': None,
    }
    if result['needs_reply'] and result['reply_kind'] == 'none':
        result['reply_kind'] = 'question'
    commitments = data.get('commitments') or []
    if not isinstance(commitments, list):
        raise ModelOutputError('commitments must be a list')
    for entry in commitments[:5]:
        if not isinstance(entry, dict):
            raise ModelOutputError('commitment must be an object')
        text = _text(entry.get('text'), 'commitment text', 160, optional=True)
        if not text:
            continue
        result['commitments'].append({
            'text': text, 'due_date': _date(entry.get('due_date')),
            'due_text': _text(entry.get('due_text'), 'due_text', 60, optional=True),
            'completed': _bool(entry.get('completed', False), 'completed'),
            'confidence': _confidence(entry.get('confidence', result['confidence']), 'commitment confidence')})
    appointment = data.get('appointment')
    if isinstance(appointment, dict) and _text(appointment.get('title'), 'title', 120, optional=True):
        status = appointment.get('status', 'proposed')
        if status not in ('proposed', 'confirmed', 'declined'):
            raise ModelOutputError('appointment status is invalid')
        result['appointment'] = {
            'title': _text(appointment['title'], 'title', 120), 'date': _date(appointment.get('date')),
            'time': _time(appointment.get('time')), 'status': status,
            'confidence': _confidence(appointment.get('confidence', result['confidence']), 'appointment confidence')}
    elif appointment not in (None, {}) and not isinstance(appointment, dict):
        raise ModelOutputError('appointment must be an object or null')
    return result


DRAFT_SYSTEM = '''You write a reply that {owner} could send as is.
Copy how {owner} writes, using the examples of {owner}'s own messages: the same language as the
conversation, the same greeting and sign-off habits, length, tone, formality and punctuation.
Answer what the other person needs using only facts in the conversation and notes. Never invent dates,
prices, places or promises; where something is unknown, say {owner} will confirm. Plain text only.'''


def draft(item: dict, contact_name: str | None, settings: dict, *, conversation: list[dict] | None = None,
          examples: list[str] | None = None, post=requests.post) -> str:
    notes = [f'To: {contact_name}' if contact_name else None, f'Situation: {item["summary"]}',
             f'Needed: {item["action"]}' if item.get('action') else None]
    if examples:
        notes += ['', f'Examples of how {settings["owner_name"]} writes:']
        notes += ['--- example\n' + text[:600] for text in examples[:settings['style_examples']]]
    if conversation:
        notes += ['', 'Conversation, oldest first:']
        notes += [f'[{"OWNER" if m["direction"] == "sent" else "CONTACT"}] {m["text"][:1200]}'
                  for m in conversation[-settings['context_messages']:]]
    content = chat([{'role': 'system', 'content': DRAFT_SYSTEM.format(owner=settings['owner_name'])},
                    {'role': 'user', 'content': '\n'.join(line for line in notes if line is not None)}],
                   settings, post=post)
    text = sources.strip_quoted_lines(content)
    if not text:
        raise ModelOutputError('empty draft')
    return text[:1500]


def available(settings: dict, *, get=requests.get) -> bool:
    try:
        response = get(settings['msty_base_url'] + '/api/tags', timeout=3)
        response.raise_for_status()
        return any(model.get('name') == settings['model'] for model in response.json().get('models', []))
    except (requests.RequestException, ValueError, AttributeError):
        return False

