"""MCP tool definitions for the attention interface. Any local MCP host can mount them."""
from __future__ import annotations

import sys
import threading

from . import api, scan

SCAN_WAIT_SECONDS = 20  # Msty Go gives up on slow tool calls; the scan keeps running after this
_scan_worker: threading.Thread | None = None
_scan_lock = threading.Lock()


def _scan(arguments):
    """Start a scan and wait briefly; a first model load can take minutes."""
    global _scan_worker
    with _scan_lock:
        if _scan_worker is None or not _scan_worker.is_alive():
            outcome = {}

            def run():
                try:
                    outcome['result'] = scan.run()
                except Exception as error:  # reported in the result and the event log
                    outcome['error'] = f'{type(error).__name__}: {error}'[:300]
                    print(f'attention scan failed: {outcome["error"]}', file=sys.stderr)
            _scan_worker = threading.Thread(target=run, name='attention-scan')
            _scan_worker.outcome = outcome
            _scan_worker.start()
        worker = _scan_worker
    worker.join(SCAN_WAIT_SECONDS)
    if worker.is_alive():
        return {'status': 'scanning', 'detail': 'The scan continues in the background; check attention_status later.'}
    if 'error' in worker.outcome:
        raise RuntimeError(worker.outcome['error'])
    return worker.outcome['result']


def _items(items):
    keys = ('id', 'kind', 'state', 'priority', 'overdue', 'review', 'confidence', 'contact_id', 'channel', 'title',
            'summary', 'action', 'due_at', 'due_text', 'event', 'snoozed_until', 'priority_reasons', 'first_seen_at')
    return {'count': len(items), 'items': [{k: item.get(k) for k in keys} for item in items]}


def _require(arguments, *names):
    missing = [name for name in names if not arguments.get(name)]
    if missing:
        raise ValueError('Missing ' + ', '.join(missing))
    return [arguments[name] for name in names]


def _kind_get(kind):
    def handler(arguments):
        item = api.get_item(_require(arguments, 'id')[0])
        if item['kind'] != kind:
            raise ValueError(f'{item["id"]} is not a {kind}')
        return item
    return handler


HANDLERS = {
    'attention_status': lambda a: api.status(),
    'attention_scan': _scan,
    'attention_brief': lambda a: api.current_brief(save=bool(a.get('archive'))),
    'attention_list': lambda a: _items(api.list_items(a.get('kind'), a.get('state'), a.get('contact_id'),
                                                      bool(a.get('include_closed')), a.get('limit', 50))),
    'attention_get': lambda a: api.get_item(_require(a, 'id')[0]),
    'attention_search': lambda a: _items(api.search(a.get('text'), a.get('contact'), bool(a.get('include_closed')))),
    'attention_complete': lambda a: api.mark_done(_require(a, 'id')[0], a.get('note')),
    'attention_snooze': lambda a: api.snooze_item(*_require(a, 'id', 'until')),
    'attention_ignore': lambda a: api.ignore_item(_require(a, 'id')[0]),
    'attention_reopen': lambda a: api.reopen_item(_require(a, 'id')[0]),
    'attention_create': lambda a: api.create_item(a.get('kind', 'reply'), *_require(a, 'title'), a.get('summary', ''),
                                                  a.get('contact'), a.get('action'), a.get('due'), a.get('due_text')),
    'attention_update': lambda a: api.update_item(_require(a, 'id')[0], **{k: a.get(k) for k in
                                                  ('title', 'summary', 'action', 'due_at', 'due_text', 'priority')}),
    'attention_draft_reply': lambda a: api.draft_reply(_require(a, 'id')[0]),
    'commitments_list': lambda a: _items(api.list_items('commitment', None if a.get('include_closed') else 'COMMITMENT_OPEN',
                                                        include_closed=bool(a.get('include_closed')))),
    'commitments_get': _kind_get('commitment'),
    'commitments_complete': lambda a: api.mark_done(_require(a, 'id')[0], a.get('note')),
    'commitments_cancel': lambda a: api.cancel_commitment(_require(a, 'id')[0]),
    'commitments_create': lambda a: api.create_item('commitment', *_require(a, 'title'), a.get('summary', ''),
                                                    a.get('contact'), a.get('title'), a.get('due'), a.get('due_text')),
    'commitments_update': lambda a: api.update_item(_require(a, 'id')[0], **{k: a.get(k) for k in
                                                    ('title', 'summary', 'due_at', 'due_text', 'priority')}),
    'contacts_get': lambda a: api.get_contact_state(_require(a, 'contact')[0]),
    'contacts_search': lambda a: {'contacts': api.search_contacts(_require(a, 'text')[0])},
    'contacts_link': lambda a: api.link_contact(*_require(a, 'channel', 'address', 'contact_id'), a.get('decision', 'confirm')),
    'appointments_list': lambda a: _items(api.get_appointment_candidates()),
    'appointments_get': _kind_get('appointment'),
    'mail_folders_status': lambda a: _organise().status(),
    'mail_folders_questions': lambda a: {'questions': _organise().pending()},
    'mail_folders_file': lambda a: {'result': _organise().file(int(_require(a, 'id')[0]), _require(a, 'folder')[0])},
    'mail_folders_undo': lambda a: {'result': _organise().undo(int(_require(a, 'move_id')[0]))},
}


def _organise():
    from . import organise
    return organise

S = {'type': 'string'}
ID = {'id': dict(S, description='Item id, e.g. reply-1a2b3c4d5e')}


def tool(name, description, properties=None, required=(), read_only=True):
    return {'name': name, 'description': description,
            'inputSchema': {'type': 'object', 'properties': properties or {}, 'required': list(required),
                            'additionalProperties': False},
            'annotations': {'readOnlyHint': read_only, 'destructiveHint': False, 'openWorldHint': False}}


KINDS = {'type': 'string', 'enum': ['reply', 'waiting', 'commitment', 'appointment']}
TOOLS = [
    tool('attention_status', 'Personal attention health: sources, Msty, counts of pending replies, commitments and waits, last scan.'),
    tool('attention_scan', 'Read new email, classify changed conversations with the local Msty model and update attention state. '
         'Returns quickly; a long scan continues in the background. Never sends anything.', read_only=False),
    tool('attention_brief', 'The current short personal attention brief: who is waiting for the user, open promises, proposed '
         'appointments. Use for "what am I forgetting?" or "who do I need to reply to?".',
         {'archive': {'type': 'boolean', 'description': 'Also save a dated copy in briefs/archive'}}),
    tool('attention_list', 'List attention items, open ones by default.',
         {'kind': KINDS, 'state': dict(S, description='e.g. needs_reply, waiting_on_me, waiting_on_other, commitment_open, '
                                           'appointment_proposed, snoozed, completed'),
          'contact_id': S, 'include_closed': {'type': 'boolean'}, 'limit': {'type': 'integer'}}),
    tool('attention_get', 'One attention item with its latest draft.', ID, ['id']),
    tool('attention_search', 'Find attention items by text and/or contact name, e.g. "What was Laura waiting for?".',
         {'text': S, 'contact': S, 'include_closed': {'type': 'boolean'}}),
    tool('attention_complete', 'Mark an item handled (reply sent, promise kept). Only when the user says so.',
         dict(ID, note=S), ['id'], read_only=False),
    tool('attention_snooze', 'Hide an item until a time: ISO date/time, "tomorrow", "3h" or "2d".',
         dict(ID, until=S), ['id', 'until'], read_only=False),
    tool('attention_ignore', 'Stop tracking an item the user says does not need attention.', ID, ['id'], read_only=False),
    tool('attention_reopen', 'Reopen a completed, ignored or snoozed item.', ID, ['id'], read_only=False),
    tool('attention_create', 'Record something to track that no source shows, e.g. a promise made in person.',
         {'kind': KINDS, 'title': S, 'summary': S, 'contact': S, 'action': S,
          'due': dict(S, description='YYYY-MM-DD only when clear'), 'due_text': dict(S, description='vague timing as said')},
         ['title'], read_only=False),
    tool('attention_update', 'Correct an item: title, summary, action, due date or priority (low/normal/high/urgent in capitals).',
         dict(ID, title=S, summary=S, action=S, due_at=S, due_text=S, priority=S), ['id'], read_only=False),
    tool('attention_draft_reply', 'Write a short local draft reply for an item and store it. It is never sent.',
         ID, ['id'], read_only=False),
    tool('commitments_list', 'Promises the user made that are still open (or all with include_closed).',
         {'include_closed': {'type': 'boolean'}}),
    tool('commitments_get', 'One commitment.', ID, ['id']),
    tool('commitments_complete', 'Mark a promise kept, e.g. "I already sent Paul the document".', dict(ID, note=S), ['id'], read_only=False),
    tool('commitments_cancel', 'Cancel a promise that no longer applies.', ID, ['id'], read_only=False),
    tool('commitments_create', 'Record a promise the user made.',
         {'title': S, 'summary': S, 'contact': S, 'due': S, 'due_text': S}, ['title'], read_only=False),
    tool('commitments_update', 'Correct a commitment.', dict(ID, title=S, summary=S, due_at=S, due_text=S, priority=S),
         ['id'], read_only=False),
    tool('contacts_get', 'A contact with identities, possible duplicates and open items.', {'contact': S}, ['contact']),
    tool('contacts_search', 'Find contacts by name or address.', {'text': S}, ['text']),
    tool('contacts_link', 'Confirm or reject that an identity (channel + address) belongs to a contact. Only on the user\'s word.',
         {'channel': S, 'address': S, 'contact_id': S, 'decision': {'type': 'string', 'enum': ['confirm', 'reject']}},
         ['channel', 'address', 'contact_id'], read_only=False),
    tool('appointments_list', 'Proposed meetings, calls or dinners found in messages, with calendar availability. '
         'Nothing is added to the calendar.'),
    tool('appointments_get', 'One appointment candidate.', ID, ['id']),
    tool('mail_folders_status', 'Email sorting: whether it is on, counts of moved, kept, held and asked emails, open '
         'questions, and the latest moves with their move ids.'),
    tool('mail_folders_questions', 'Emails the sorter was unsure about, with its suggested folders. Ask the user where '
         'each goes; never guess.'),
    tool('mail_folders_file', 'File an email the sorter asked about, only with the user\'s answer: an existing folder, '
         'a new folder name (created), or "keep" to leave it in the inbox. The sender is filed there from then on.',
         {'id': dict(S, description='Question id from mail_folders_questions'), 'folder': S}, ['id', 'folder'], read_only=False),
    tool('mail_folders_undo', 'Move a sorted email back to the inbox, by move id from mail_folders_status.',
         {'move_id': S}, ['move_id'], read_only=False),
]

# The compact set mounted into the existing CONSENSUS MCP connection in Msty Go.
COMPACT = ['attention_status', 'attention_scan', 'attention_brief', 'attention_list', 'attention_search', 'attention_get',
           'attention_complete', 'attention_snooze', 'attention_ignore', 'attention_create',
           'mail_folders_status', 'mail_folders_questions', 'mail_folders_file', 'mail_folders_undo']


def call(name: str, arguments: dict | None = None):
    if name not in HANDLERS:
        raise KeyError(f'Unknown tool {name}')
    return HANDLERS[name](arguments or {})
