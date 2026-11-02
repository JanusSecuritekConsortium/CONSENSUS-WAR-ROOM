"""Attach memory packs where they are used, and let the owner approve Msty Go's memory suggestions from Telegram.

    python -m integrations.msty.memory_review mount DB   # attach packs to folders and bots (Msty Go closed)
    python -m integrations.msty.memory_review ask        # send unasked suggestions to Telegram
    python -m integrations.msty.memory_review pending

Which packs go where is a local setting ("mounts" in memory_packs.json beside the packs), never in this repository:
{"folders": {"Folder name": ["Default pack", "Other pack"]}, "bots": ["Pack"]}. The first pack of a folder is its
default, where accepted suggestions are saved; attaching also turns on the folder's learning so Msty Go suggests
memories from its chats. Suggestions are only read from and written to the local Msty Go database.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys

from integrations.msty import memory_packs as mp

ENTRY_KINDS = {'fact': 'facts', 'constraint': 'constraints', 'decision': 'decisions'}
ITEM_KINDS = {'task': ('open_tasks', 'open'), 'artifact': ('artifacts', 'current')}


def msty_db() -> Path:
    return Path(os.environ['APPDATA']) / 'Msty Go' / 'msty-go.db'


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    db = sqlite3.connect(db_path or msty_db(), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=30000')
    return db


def stamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')


def plan() -> dict:
    return json.loads(mp.settings_path().read_text(encoding='utf-8')).get('mounts', {})


def mount(db_path: Path | None = None, mounts: dict | None = None, *, now=None) -> dict:
    """Attach packs by title to folders (by name) and to every bot. Existing attachments are kept."""
    mounts = plan() if mounts is None else mounts
    when = stamp(now or datetime.now(timezone.utc))
    result = {'attached': 0, 'missing': []}
    db = connect(db_path)
    try:
        with db:
            packs = {row['title']: row['id'] for row in db.execute('SELECT id, title FROM memory_packs WHERE archived=0')}

            def attach(owner_type, owner_id, titles):
                for title in titles:
                    if title not in packs:
                        result['missing'].append(title)
                        continue
                    result['attached'] += db.execute(
                        'INSERT OR IGNORE INTO memory_mounts(owner_type,owner_id,pack_id,created_at) VALUES(?,?,?,?)',
                        (owner_type, owner_id, packs[title], when)).rowcount
            for name, titles in mounts.get('folders', {}).items():
                folder = db.execute('SELECT id FROM chat_folders WHERE name=?', (name,)).fetchone()
                if not folder:
                    result['missing'].append(name)
                    continue
                attach('folder', folder['id'], titles)
                if titles and titles[0] in packs:
                    db.execute('UPDATE chat_folders SET default_pack_id=?, learning_enabled=1, updated_at=? WHERE id=?',
                               (packs[titles[0]], when, folder['id']))
            for bot in db.execute('SELECT id FROM bots').fetchall():
                attach('bot', bot['id'], mounts.get('bots', []))
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('Msty Go database failed its check after attaching packs')
    finally:
        db.close()
    return result


def pending(db_path: Path | None = None, limit: int = 20) -> list[dict]:
    db = connect(db_path)
    try:
        rows = db.execute('SELECT c.id, c.kind, c.key, c.value, f.name AS folder FROM folder_memory_candidates c '
                          "JOIN chat_folders f ON f.id=c.folder_id WHERE c.status='pending' ORDER BY c.created_at LIMIT ?",
                          (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


def decide(candidate_id: str, keep: bool, *, db_path: Path | None = None, now=None) -> str:
    """Accept a suggestion into its folder's default pack as a new revision, or dismiss it."""
    when = stamp(now or datetime.now(timezone.utc))
    db = connect(db_path)
    try:
        with db:
            row = db.execute('SELECT c.*, f.default_pack_id FROM folder_memory_candidates c JOIN chat_folders f '
                             'ON f.id=c.folder_id WHERE c.id=?', (candidate_id,)).fetchone()
            if not row:
                return 'That memory suggestion no longer exists.'
            if row['status'] != 'pending':
                return f'Already {row["status"]}.'
            label = row['key'] or row['value'][:80]
            if not keep:
                db.execute("UPDATE folder_memory_candidates SET status='dismissed', updated_at=? WHERE id=?", (when, row['id']))
                return 'Not remembered: ' + label
            pack = db.execute('SELECT p.id, p.title, r.state_json FROM memory_packs p LEFT JOIN memory_pack_revisions r '
                              'ON r.id=p.current_revision_id WHERE p.id=?', (row['default_pack_id'],)).fetchone()
            if not pack:
                return 'This folder has no memory pack to save into. Pick one in Msty Go.'
            state = json.loads(pack['state_json'] or '{}')
            for name in ('facts', 'constraints', 'decisions', 'open_tasks', 'artifacts', 'tags', 'evidence_refs'):
                state.setdefault(name, [])
            state.setdefault('durable_summary', '')
            item_id = mp.stable_id('candidate', row['id'])
            if row['kind'] in ENTRY_KINDS:
                section = ENTRY_KINDS[row['kind']]
                state[section].append({'id': item_id, 'key': (row['key'] or row['value'])[:120],
                                       'value': row['value'][:400], 'status': 'current'})
            else:
                section, status = ITEM_KINDS[row['kind']]
                state[section].append({'id': item_id, 'title': (row['key'] or row['value'])[:180], 'status': status,
                                       **({'detail': row['value'][:500]} if row['key'] else {})})
            state[section] = state[section][-32:]  # Msty keeps 32 per section; the newest win
            mp.write_revision(db, pack['id'], pack['title'], mp.stable_id('revision', 'candidate', row['id']), state,
                              'Accepted memory suggestion', when)
            db.execute("UPDATE folder_memory_candidates SET status='accepted', updated_at=? WHERE id=?", (when, row['id']))
            return f'Remembered in {pack["title"]}: {label}'
    finally:
        db.close()


def asked_path() -> Path:
    return mp.OUTPUT / 'review-asked.json'


def ask(limit: int = 5, *, db_path: Path | None = None, now=None, send=None) -> int:
    """Send up to `limit` unasked suggestions to the owner's Aurelius chat with Remember / Skip buttons."""
    now = now or datetime.now(timezone.utc)
    path = asked_path()
    asked = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    fresh = [c for c in pending(db_path, limit=200) if c['id'] not in asked][:limit]
    for candidate in fresh:
        text = (f'Remember this? ({candidate["folder"]}, {candidate["kind"]})\n'
                + (f'{candidate["key"]}: ' if candidate['key'] else '') + candidate['value'])
        (send or telegram_send)(text, candidate['id'], now)
        asked[candidate['id']] = now.isoformat()
        path.write_text(json.dumps(asked), encoding='utf-8')
    return len(fresh)


def telegram_send(text: str, candidate_id: str, now: datetime) -> None:
    from integrations.msty.personal import interaction_store, publication
    route = publication.telegram_route()
    markup = interaction_store.keyboard(route, [[('Remember', 'memory', {'c': candidate_id, 'keep': True}),
                                                 ('Skip', 'memory', {'c': candidate_id, 'keep': False})]], now=now)
    result = publication.telegram_call(route, 'sendMessage', {'chat_id': route['chat_id'], 'text': text,
                                                               'reply_markup': markup})
    interaction_store.bind(route, markup, result['message_id'])


def answer_button(payload: dict) -> str:
    """A Telegram button press from the owner's own chat (already authenticated by the relay)."""
    return decide(str(payload['c']), bool(payload.get('keep')))


def main(argv=None) -> int:
    args = argv or sys.argv[1:] or ['pending']
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    if args[0] == 'mount':
        result = mount(Path(args[1]) if len(args) > 1 else None)
    elif args[0] == 'ask':
        result = {'sent': ask()}
    else:
        result = pending()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
