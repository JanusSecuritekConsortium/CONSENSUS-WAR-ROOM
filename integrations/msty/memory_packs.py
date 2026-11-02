"""Turn Markdown notes into Msty Go memory packs, one pack per topic, with the local model.

    python -m integrations.msty.memory_packs topics            # group notes and save the plan
    python -m integrations.msty.memory_packs build [TOPIC ...] # condense topics into packs
    python -m integrations.msty.memory_packs list
    python -m integrations.msty.memory_packs install DB         # into a closed Msty Go database (back it up first)

Sources and the output folder are local settings (memory_packs.json beside the output), never in this
repository, because the notes and the packs are personal. Chat exports contribute the owner's own
messages first; other notes their opening text. Every model call goes to the local Msty endpoint only.
A pack follows Msty Go's memory pack limits: a summary of 1,200 characters and at most 32 facts,
constraints, decisions, tasks and artifacts, and 16 tags.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import requests

from integrations.attention import config as attention_config

OUTPUT = Path(r'G:\Msty\MstyWiki\memory-packs')
DEFAULT_SOURCES = {
    # A folder whose subfolders are topics; loose notes directly inside it are grouped by the model.
    'grouped': [r'G:\Msty\MstyWiki\wiki'],
    # A folder that is one topic each.
    'topics': {},
    'skip': ['images', '.obsidian', '.trash'],
}
NOTE_CHARS = 900          # per note in a topic digest
CHUNK_CHARS = 16_000      # per model call; with the answer it fits CONTEXT
MAX_LOOSE_TOPICS = 20
CONTEXT = 16_384          # a 32k context crashed the local server on this GPU

ENTRY = {'type': 'object', 'properties': {'key': {'type': 'string'}, 'value': {'type': 'string'}},
         'required': ['key', 'value']}
ITEM = {'type': 'object', 'properties': {'title': {'type': 'string'}, 'detail': {'type': 'string'}},
        'required': ['title', 'detail']}
STATE = {'type': 'object', 'properties': {
    'durable_summary': {'type': 'string'}, 'facts': {'type': 'array', 'items': ENTRY},
    'constraints': {'type': 'array', 'items': ENTRY}, 'decisions': {'type': 'array', 'items': ENTRY},
    'open_tasks': {'type': 'array', 'items': ITEM}, 'artifacts': {'type': 'array', 'items': ITEM},
    'tags': {'type': 'array', 'items': {'type': 'string'}}},
    'required': ['durable_summary', 'facts', 'constraints', 'decisions', 'open_tasks', 'artifacts', 'tags']}

CONDENSE = '''You build a durable memory pack about the topic "{topic}" for the owner's personal assistant.
The notes below are the owner's own notes and conversations ([OWNER] lines are the owner's words).
Keep only what stays useful later: facts about the owner, their situation, people, places, accounts and
preferences; rules they follow (constraints); choices they made (decisions); unfinished things (open_tasks);
documents, devices or projects they have (artifacts). Skip general knowledge any assistant already knows.
Write in English. Each key is 2 to 6 words; each value one short sentence. Never invent anything.
durable_summary: at most 1,000 characters. At most 32 entries per list and 16 lowercase tags.'''

MERGE = '''Merge these partial memory packs about "{topic}" into one. Remove duplicates, keep the most specific
and most recent facts, at most 32 entries per list and 16 lowercase tags, summary at most 1,000 characters.
Never invent anything.'''

GROUP = '''These are titles of the owner's saved conversations. Propose at most {n} topics that group them
well (for example "Taxes and finances", "Health", "Home and moving"). Answer JSON {{"topics": [names]}}.'''

ASSIGN = '''Assign each numbered title to exactly one of these topics: {topics}. Use "Other" when none fits.
Answer JSON {{"assign": {{"<number>": "<topic>"}}}}.'''


def settings_path() -> Path:
    return OUTPUT / 'memory_packs.json'


def load_sources() -> dict:
    if not settings_path().exists():
        return dict(DEFAULT_SOURCES)
    return {**DEFAULT_SOURCES, **json.loads(settings_path().read_text(encoding='utf-8'))}  # a broken file must fail loudly


def chat(messages, schema, *, post=requests.post) -> dict:
    settings = attention_config.load()
    body = {'model': settings['model'], 'messages': messages, 'stream': False, 'think': False, 'format': schema,
            'keep_alive': '30m', 'options': {'temperature': 0, 'num_ctx': CONTEXT}}
    response = post(settings['msty_base_url'] + '/api/chat', json=body, timeout=(5, 900))
    response.raise_for_status()
    return json.loads(response.json()['message']['content'])


def read_note(path: Path) -> dict:
    text = path.read_text(encoding='utf-8', errors='replace')
    front = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    body = text[front.end():] if front else text
    title = re.search(r'^title:\s*"?(.*?)"?\s*$', front[1], re.M)[1] if front and re.search(r'^title:', front[1], re.M) else \
        re.sub(r'^\d{4}-\d{2}-\d{2}-', '', path.stem).replace('_', ' ')
    date = re.search(r'^(?:originalDate|date):\s*(\S+)', front[1], re.M) if front else None
    return {'path': str(path), 'title': title.strip(), 'date': date[1] if date else '', 'body': body}


def digest(note: dict, limit: int = NOTE_CHARS) -> str:
    """The owner's own words first: chat exports keep only their messages."""
    turns = re.split(r'^## (You|ChatGPT|User|Assistant|Claude)\s*$', note['body'], flags=re.M)
    if len(turns) > 2:
        mine = [re.sub(r'^`[^`]*`.*$', '', turns[i + 1], flags=re.M).strip(' \n-')
                for i in range(1, len(turns) - 1, 2) if turns[i] in ('You', 'User')]
        text = ' / '.join('[OWNER] ' + re.sub(r'\s+', ' ', m)[:300] for m in mine if m)
    else:
        text = re.sub(r'\s+', ' ', note['body'])
    return f'## {note["title"]} ({note["date"]})\n{text[:limit]}'


def notes_in(folder: Path, skip: list[str], recursive=True) -> list[Path]:
    pattern = folder.rglob('*.md') if recursive else folder.glob('*.md')
    return sorted(p for p in pattern if not any(part in skip for part in p.relative_to(folder).parts))


def plan_topics(*, post=requests.post) -> dict:
    """Topic name -> note paths. Subfolders are topics; loose notes are grouped by title with the model."""
    sources = load_sources()
    topics: dict[str, list[str]] = {}
    for root in map(Path, sources['grouped']):
        for sub in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in sources['skip']):
            found = notes_in(sub, sources['skip'])
            if found:
                topics[sub.name] = [str(p) for p in found]
        loose = [read_note(p) for p in notes_in(root, sources['skip'], recursive=False)]
        if loose:
            titles = '\n'.join(n['title'] for n in loose)
            names = chat([{'role': 'system', 'content': GROUP.format(n=MAX_LOOSE_TOPICS)}, {'role': 'user', 'content': titles}],
                         {'type': 'object', 'properties': {'topics': {'type': 'array', 'items': {'type': 'string'}}},
                          'required': ['topics']}, post=post)['topics'][:MAX_LOOSE_TOPICS]
            allowed = {n.casefold(): n for n in names + ['Other']}
            for start in range(0, len(loose), 80):
                batch = loose[start:start + 80]
                answer = chat([{'role': 'system', 'content': ASSIGN.format(topics=json.dumps(names + ['Other']))},
                               {'role': 'user', 'content': '\n'.join(f'{i}. {n["title"]}' for i, n in enumerate(batch))}],
                              {'type': 'object', 'properties': {'assign': {'type': 'object'}}, 'required': ['assign']},
                              post=post)['assign']
                for i, note in enumerate(batch):
                    name = allowed.get(str(answer.get(str(i), 'Other')).casefold(), 'Other')
                    topics.setdefault(name, []).append(note['path'])
    for name, folder in sources['topics'].items():
        found = notes_in(Path(folder), sources['skip'])
        if found:
            topics[name] = [str(p) for p in found]
    return topics


def clip_state(state: dict) -> dict:
    def entries(items):
        return [{'key': str(e.get('key', ''))[:120], 'value': str(e.get('value', ''))[:400]}
                for e in items or [] if e.get('key') and e.get('value')][:32]

    def things(items):
        return [{'title': str(e.get('title', ''))[:180], 'detail': str(e.get('detail', ''))[:500]}
                for e in items or [] if e.get('title')][:32]
    tags = list(dict.fromkeys(str(t).strip().lower()[:40] for t in state.get('tags') or [] if str(t).strip()))[:16]
    return {'durable_summary': str(state.get('durable_summary', ''))[:1200], 'facts': entries(state.get('facts')),
            'constraints': entries(state.get('constraints')), 'decisions': entries(state.get('decisions')),
            'open_tasks': things(state.get('open_tasks')), 'artifacts': things(state.get('artifacts')), 'tags': tags}


def condense(topic: str, paths: list[str], *, post=requests.post) -> dict:
    notes = sorted((read_note(Path(p)) for p in paths), key=lambda n: n['date'], reverse=True)  # newest first
    chunks, current = [], ''
    for note in notes:
        part = digest(note)
        if current and len(current) + len(part) > CHUNK_CHARS:
            chunks.append(current)
            current = ''
        current += part + '\n\n'
    chunks.append(current)
    system = {'role': 'system', 'content': CONDENSE.format(topic=topic)}
    partial = [clip_state(chat([system, {'role': 'user', 'content': chunk}], STATE, post=post)) for chunk in chunks]
    if len(partial) == 1:
        return partial[0]
    merged = chat([{'role': 'system', 'content': MERGE.format(topic=topic)},
                   {'role': 'user', 'content': json.dumps(partial, ensure_ascii=False)[:CHUNK_CHARS]}], STATE, post=post)
    return clip_state(merged)


def stable_id(*parts: str) -> str:
    return hashlib.sha256('\0'.join(parts).encode()).hexdigest()[:21]


def envelope(topic: str, state: dict, now: datetime) -> dict:
    """The pack and its revision, in the shape Msty Go's importMemoryPackSnapshot takes."""
    pack_id, revision_id = stable_id('pack', topic), stable_id('revision', topic, json.dumps(state, sort_keys=True))
    return {'pack': {'id': pack_id, 'title': topic, 'archived': False, 'currentRevisionId': revision_id},
            'revisions': [{'id': revision_id, 'revisionNumber': 1, 'state': state, 'reason': 'Imported from Markdown notes',
                           'createdAt': now.isoformat()}]}


def file_name(topic: str) -> str:
    return re.sub(r'[^\w-]+', '_', topic).strip('_')[:60] + '.mc.mem'


def build(topics: list[str] | None = None, *, post=requests.post, now=None, sleep=time.sleep) -> dict:
    """Named topics are rebuilt; without names, only topics with no pack yet. One failure never stops the rest."""
    now = now or datetime.now(timezone.utc)
    plan = json.loads((OUTPUT / 'topics.json').read_text(encoding='utf-8'))
    result = {'built': [], 'failed': []}
    for topic, paths in plan.items():
        if topics and topic not in topics or not topics and (OUTPUT / file_name(topic)).exists():
            continue
        for attempt in (1, 2):
            try:
                state = condense(topic, paths, post=post)
                break
            except (requests.RequestException, ValueError, KeyError):
                state = None
                if attempt == 1:
                    sleep(60)  # the local server restarts itself after a crash
        if state is None:
            result['failed'].append(topic)
            continue
        (OUTPUT / file_name(topic)).write_text(json.dumps(envelope(topic, state, now), ensure_ascii=False, indent=2),
                                              encoding='utf-8')
        result['built'].append(topic)
    return result


def stored_state(state: dict, pack_id: str) -> dict:
    """The state as Msty Go stores it (normalizeMemoryPackState): every item gets an id and a status."""
    def entries(name):
        return [{'id': stable_id(pack_id, name, e['key']), 'key': e['key'], 'value': e['value'], 'status': 'current'}
                for e in state.get(name, [])]

    def items(name, status):
        return [{'id': stable_id(pack_id, name, i['title']), 'title': i['title'], 'status': status,
                 **({'detail': i['detail']} if i.get('detail') else {})} for i in state.get(name, [])]
    return {'durable_summary': state.get('durable_summary', ''), 'facts': entries('facts'),
            'constraints': entries('constraints'), 'decisions': entries('decisions'), 'open_tasks': items('open_tasks', 'open'),
            'artifacts': items('artifacts', 'current'), 'tags': state.get('tags', []), 'evidence_refs': []}


def write_revision(db, pack_id: str, title: str, revision_id: str, state: dict, reason: str, stamp: str) -> int:
    """Add a revision of a pack in Msty Go's stored shape, make it current and refresh the pack's search entry."""
    number = db.execute('SELECT COALESCE(MAX(revision_number), 0) + 1 FROM memory_pack_revisions WHERE pack_id=?',
                        (pack_id,)).fetchone()[0]
    if number == 1:
        db.execute('INSERT INTO memory_packs(id,title,archived,created_at,updated_at) VALUES(?,?,0,?,?)',
                   (pack_id, title, stamp, stamp))
    db.execute('INSERT INTO memory_pack_revisions(id,pack_id,revision_number,state_json,revision_reason,created_at) '
               'VALUES(?,?,?,?,?,?)', (revision_id, pack_id, number, json.dumps(state, ensure_ascii=False), reason, stamp))
    db.execute('UPDATE memory_packs SET title=?, current_revision_id=?, updated_at=? WHERE id=?',
               (title, revision_id, stamp, pack_id))
    content = '\n'.join([f"{e['key']}: {e['value']}" for k in ('facts', 'constraints', 'decisions') for e in state[k]]
                        + [i['title'] for k in ('open_tasks', 'artifacts') for i in state[k]])
    old = db.execute('SELECT id FROM memory_pack_search_docs WHERE pack_id=?', (pack_id,)).fetchone()
    if old:
        db.execute('DELETE FROM memory_pack_fts WHERE rowid=?', old)
        db.execute('DELETE FROM memory_pack_search_docs WHERE id=?', old)
    doc = db.execute('INSERT INTO memory_pack_search_docs(pack_id,revision_id,title,summary,tags_json,content_text,'
                     'updated_at) VALUES(?,?,?,?,?,?,?)', (pack_id, revision_id, title[:160], state['durable_summary'],
                                                          json.dumps(state['tags']), content, stamp)).lastrowid
    db.execute('INSERT INTO memory_pack_fts(rowid,title,summary,tags,content_text) VALUES(?,?,?,?,?)',
               (doc, title[:160], state['durable_summary'], ' '.join(state['tags']), content))
    return number


def install(db_path: Path, files: list[Path], *, now=None) -> dict:
    """Put packs into the Msty Go database the way importMemoryPackSnapshot does, including its search index.

    Msty Go must be closed. A pack already holding the same revision is left alone; a changed one gets a new
    revision. Nothing else in the database is touched."""
    import sqlite3
    stamp = (now or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    result = {'added': [], 'updated': [], 'unchanged': []}
    db = sqlite3.connect(db_path)
    try:
        with db:
            for path in files:
                snapshot = json.loads(path.read_text(encoding='utf-8'))
                pack, revision = snapshot['pack'], snapshot['revisions'][-1]
                state = stored_state(clip_state(revision['state']), pack['id'])
                if db.execute('SELECT 1 FROM memory_pack_revisions WHERE id=?', (revision['id'],)).fetchone():
                    result['unchanged'].append(pack['title'])
                    continue
                number = write_revision(db, pack['id'], pack['title'], revision['id'], state, revision['reason'], stamp)
                result['updated' if number > 1 else 'added'].append(pack['title'])
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Msty Go database failed its integrity check after installing packs')
    finally:
        db.close()
    return result


def main(argv=None) -> int:
    args = argv or sys.argv[1:] or ['list']
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    if args[0] == 'topics':
        plan = plan_topics()
        (OUTPUT / 'topics.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
        args = ['list']
    if args[0] == 'build':
        print(json.dumps(build(args[1:] or None), ensure_ascii=False))
    elif args[0] == 'install':
        print(json.dumps(install(Path(args[1]), sorted(OUTPUT.glob('*.mc.mem'))), ensure_ascii=False))
    elif args[0] == 'list':
        plan = json.loads((OUTPUT / 'topics.json').read_text(encoding='utf-8')) if (OUTPUT / 'topics.json').exists() else {}
        for topic, paths in sorted(plan.items(), key=lambda kv: -len(kv[1])):
            print(f'{len(paths):5} {topic}{"  (built)" if (OUTPUT / file_name(topic)).exists() else ""}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
