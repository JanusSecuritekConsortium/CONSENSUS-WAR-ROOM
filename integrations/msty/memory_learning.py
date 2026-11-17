"""Aurelius learns lasting facts about the owner from its own chats, every night, without an approval step.

    python -m integrations.msty.memory_learning run          # learn from new messages, save, report on Telegram
    python -m integrations.msty.memory_learning run --dry    # show what it would learn; saves and sends nothing

Only the owner's own words in the Aurelius chats (Telegram and mobile) are read, from the local Msty Go
database, by the local model; forwarded content is skipped. Each learned fact goes into the shared memory
pack both Aurelius agents already read, so later answers and briefings use it. The owner gets one Telegram
message listing what was learned, with a Forget button per fact. Where it stopped is kept in the private
store, so every message is read once.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import re
import sqlite3
import sys

from integrations.msty import aurelius_memory as memory

CHUNK_CHARS = 12_000   # owner text per model call
MAX_FACTS = 8          # per model call
MIN_CHARS = 15         # "ok", "1", "Hello Aurelius" carry nothing to learn
FORWARDED = re.compile(r'reenviad|forwarded', re.I)

SCHEMA = {'type': 'object', 'properties': {'facts': {'type': 'array', 'items': {
    'type': 'object', 'properties': {'key': {'type': 'string'}, 'value': {'type': 'string'}},
    'required': ['key', 'value']}}}, 'required': ['facts']}

PROMPT = '''You keep the long-term memory of the owner's personal assistant, Aurelius.
Below are messages the owner wrote to Aurelius. Pick out at most {n} LASTING facts worth remembering for
future conversations: the owner's preferences and habits, people in their life and who they are, places,
ongoing projects and commitments, plans with dates, and decisions they made.

Rules:
- Only what the owner clearly stated about themselves or their life. Never guess or invent.
- Skip one-off requests ("what is next?", "read it aloud"), questions, small talk and general knowledge.
- Never save passwords, codes, account or card numbers, or medical details.
- key: 2 to 5 lowercase words joined by underscores, e.g. "preferred_briefing_format".
  If a fact updates one already known, reuse its key exactly.
- value: one short sentence in English.
- If nothing lasting was said, return an empty list.

Already known:
{known}

Owner's messages:
{messages}'''


def bot_ids(db: sqlite3.Connection) -> list[str]:
    """The Telegram and mobile Aurelius agents."""
    return [row[0] for row in db.execute('SELECT id, name FROM bots')
            if 'aurelius' in re.sub(r'[^a-z]', '', str(row[1]).casefold())]


def owner_text(content: str) -> str | None:
    """The owner's own words from one stored user message, or None when there is nothing of theirs."""
    content = (content or '').strip()
    if content.startswith('[MCP Client]:'):
        # A Telegram turn sent by the relay: a source label, instructions, then "Mensaje:\n<text>\n/no_think".
        if 'Mensaje:\n' not in content:
            return None  # scheduled reports and other tool prompts
        head, _, text = content.partition('Mensaje:\n')
        if FORWARDED.search(head):
            return None  # someone else's words
        text = text.rsplit('\n/no_think', 1)[0]
    else:
        text = re.sub(r'^\[[^\]\n]{1,60}\]:\s*', '', content)  # mobile chats prefix the sender's name
    text = text.strip()
    return text if len(text) >= MIN_CHARS else None


def new_messages(after: int, *, db_path=None) -> tuple[list[dict], int]:
    """Owner messages to Aurelius stored after rowid `after`, and the newest rowid seen."""
    path = (db_path or memory.database_path()).resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=10)) as db:
        bots = bot_ids(db)
        if not bots:
            return [], after
        marks = ','.join('?' * len(bots))
        rows = db.execute(f"SELECT m.rowid, m.content, m.created_at FROM messages m JOIN conversations c "
                          f"ON c.id=m.conversation_id WHERE m.rowid>? AND m.role='user' AND c.bot_id IN ({marks}) "
                          f"ORDER BY m.rowid", (after, *bots)).fetchall()
        last = db.execute('SELECT COALESCE(MAX(rowid), ?) FROM messages', (after,)).fetchone()[0]
    found = [{'at': at[:10], 'text': text} for _, content, at in rows if (text := owner_text(content))]
    return found, last


def chunks(messages: list[dict]) -> list[str]:
    parts, current = [], ''
    for message in messages:
        line = f'[{message["at"]}] {message["text"][:2000]}\n'
        if current and len(current) + len(line) > CHUNK_CHARS:
            parts.append(current)
            current = ''
        current += line
    return parts + ([current] if current else [])


def known_facts(*, db_path=None) -> str:
    facts = memory.recall(db_path=db_path)['facts']
    return '\n'.join(f'- {f.get("key")}: {f.get("value")}' for f in facts[:30]) or '(nothing yet)'


def learn(text: str, known: str, *, chat=None) -> list[dict]:
    if chat is None:
        from integrations.msty.memory_packs import chat
    answer = chat([{'role': 'user', 'content': PROMPT.format(n=MAX_FACTS, known=known, messages=text)}], SCHEMA)
    facts = answer.get('facts') if isinstance(answer, dict) else None
    return [f for f in (facts or []) if isinstance(f, dict) and f.get('key') and f.get('value')][:MAX_FACTS]


def state_path():
    from integrations.msty.personal import store
    return store.ROOT / 'memory-learning.json'


def report(saved: list[dict], now: datetime, *, send=None) -> None:
    lines = ['I learned this from our recent chats:'] + [f'- {f["key"].replace("_", " ")}: {f["value"]}' for f in saved]
    lines.append('Tap Forget on anything wrong (until tomorrow evening), or ask me to forget it any time.')
    (send or telegram_send)('\n'.join(lines), [f['key'] for f in saved], now)


def telegram_send(text: str, keys: list[str], now: datetime) -> None:
    from integrations.msty.personal import interaction_store, publication
    route = publication.telegram_route()
    rows = [[('Forget: ' + key.replace('_', ' ')[:40], 'memory_forget', {'k': key})] for key in keys]
    markup = interaction_store.keyboard(route, rows, now=now)
    result = publication.telegram_call(route, 'sendMessage', {'chat_id': route['chat_id'], 'text': text[:4000],
                                                               'reply_markup': markup})
    interaction_store.bind(route, markup, result['message_id'])


def answer_forget(payload: dict) -> str:
    """The Forget button, pressed in the owner's own chat (already authenticated by the relay)."""
    key = str(payload['k'])
    done = memory.forget(key, 'telegram').get('forgotten')
    return ('Forgotten: ' if done else 'Already gone: ') + key.replace('_', ' ')


def run(*, dry=False, chat=None, send=None, db_path=None, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    path = state_path()
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    messages, last = new_messages(int(state.get('after', 0)), db_path=db_path)
    learned, saved, refused = [], [], 0
    for text in chunks(messages):
        learned += learn(text, known_facts(db_path=db_path), chat=chat)
        if dry:
            continue
        for fact in learned[len(saved) + refused:]:
            try:
                result = memory.remember(fact['key'], fact['value'], 'telegram', learned=True, db_path=db_path)
            except ValueError:
                refused += 1  # a credential, a bad key or a full pack: never saved
                continue
            if result.get('unchanged'):
                refused += 1
            else:
                saved.append({'key': result['key'], 'value': result['value']})
    if not dry:
        if saved:
            report(saved, now, send=send)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'after': last, 'checked_at': now.isoformat()}), encoding='utf-8')
    return {'messages': len(messages), 'learned': learned if dry else saved, 'skipped': refused, 'dry_run': dry}


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] != 'run':
        print(__doc__)
        return 2
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    result = run(dry='--dry' in args)
    print(json.dumps(result, ensure_ascii=False, indent=2) if '--dry' in args else
          json.dumps({k: (len(v) if k == 'learned' else v) for k, v in result.items()}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
