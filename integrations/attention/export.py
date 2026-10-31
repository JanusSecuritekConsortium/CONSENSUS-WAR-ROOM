"""Deterministic Markdown projection of the attention database.

Files are regenerated from SQLite. A file edited by hand since it was written is
copied to system/conflicts before it is replaced, so no edit is lost silently.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import shutil

from . import brief, config, log, priority, store

FOOTER = ('\n---\n_Generated from the attention database. Change it with the attention tools or '
          '`python -m integrations.attention`; manual edits are kept in system/conflicts, then replaced._\n')

SCHEMA_DOC = '''# Personal attention: shared state

`system/state.sqlite3` is the single source of truth. Every Markdown file in this folder is
generated from it after each change, so tools can read plain files and people can browse them.
Change state through the attention tools (MCP) or the command line, not by editing files.
Copying the whole folder copies the complete state. Credentials are never stored here.

## Item frontmatter

| field | meaning |
|---|---|
| id | stable id; the same conversation event always gets the same id |
| type | reply, waiting, commitment or appointment |
| state | needs_reply, waiting_on_me, waiting_on_other, commitment_open, appointment_proposed, snoozed, completed, ignored, cancelled |
| status | commitments only: open, overdue, done or cancelled |
| priority | low, normal, high or urgent, with the reasons in the body |
| confidence | classifier confidence; review: true means it needs your confirmation |
| contact_id | file name in contacts/ |
| channel | email, telegram, whatsapp or manual |
| due | YYYY-MM-DD or a timestamp when known; due_text keeps vague timing ("next week") |
| source_id | account and message reference in the original source |

Folders: attention/{open,snoozed,completed}, commitments/{open,completed},
appointments/{proposed,resolved}, contacts/, briefs/{current.md,archive/}, system/.
Closed items stay in the completed folders for the retention period in system/settings.json.
Conversation text is not stored; only summaries, actions and references.
'''


def scalar(value) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value)
    plain = text.replace('-', '').replace('_', '').replace('.', '').replace(':', '').replace('+', '').isalnum()
    reserved = text.casefold() in ('null', 'true', 'false', 'yes', 'no', 'on', 'off')
    return text if plain and not reserved and not text[0].isdigit() else json.dumps(text, ensure_ascii=False)


def frontmatter(fields: dict) -> str:
    return '---\n' + ''.join(f'{key}: {scalar(value)}\n' for key, value in fields.items()) + '---\n'


def folder(item: dict) -> str:
    closed = item['state'] in store.CLOSED
    if item['kind'] == 'commitment':
        return 'commitments/' + ('completed' if closed else 'open')
    if item['kind'] == 'appointment':
        return 'appointments/' + ('resolved' if closed else 'proposed')
    return 'attention/' + ('completed' if closed else 'snoozed' if item['state'] == store.SNOOZED else 'open')


def commitment_status(item: dict) -> str:
    if item['state'] == store.CANCELLED:
        return 'cancelled'
    if item['state'] in store.CLOSED:
        return 'done'
    return 'overdue' if item['overdue'] else 'open'


def render_item(item: dict, contact: dict | None, draft: dict | None, settings: dict) -> str:
    fields = {'id': item['id'], 'type': item['kind'], 'state': item['state'].lower()}
    if item['kind'] == 'commitment':
        fields['status'] = commitment_status(item)
    fields.update(priority=item['priority'].lower(), overdue=item['overdue'], confidence=item['confidence'],
                  review=item['review'], contact_id=item['contact_id'], channel=item['channel'],
                  created=item['created_at'], updated=item['updated_at'], first_seen=item['first_seen_at'],
                  due=item['due_at'], due_text=item['due_text'], snoozed_until=item['snoozed_until'],
                  resolution=item['resolution'], source_id=item['source_ref'], origin=item['origin'])
    title = item['title']
    lines = [frontmatter(fields), f'# {title}', '', item['summary'], '']
    if item.get('action') and item['state'] not in store.CLOSED:
        lines += ['## Required action', '', item['action'], '']
    if item['priority_reasons']:
        lines += ['## Priority', '', f'{item["priority"]}: ' + '; '.join(item['priority_reasons']) + '.', '']
    event = item.get('event')
    if event:
        lines += ['## Calendar', '', brief.event_text(event, settings) + '.']
        if event.get('availability_detail'):
            lines.append(event['availability_detail'] + '.')
        lines.append('')
    if contact:
        lines += ['## Contact', '', f'[[{contact["id"]}|{contact["name"]}]]', '']
    if draft:
        lines += ['## Draft', '', draft['body'], '', '_Not sent. Sending stays with you._', '']
    return '\n'.join(lines).rstrip() + '\n' + FOOTER


def render_contact(contact: dict, identities: list, proposals: list, items: list[dict]) -> str:
    lines = [frontmatter({'id': contact['id'], 'name': contact['name'], 'updated': contact['updated_at']}),
             f'# {contact["name"]}', '', '## Identities', '']
    lines += [f'- {row["channel"]}: {row["address"]}' + (f' ({row["display_name"]})' if row['display_name'] else '')
              for row in identities] or ['- none']
    if proposals:
        lines += ['', '## Possible same person (not merged)', '']
        lines += [f'- {row["channel"]}: {row["address"]} may also be [[{row["contact_id"]}]] ({row["reason"]}); '
                  f'confirm with `contacts link`' for row in proposals]
    open_items = [i for i in items if i['state'] not in store.CLOSED]
    lines += ['', '## Open items', '']
    lines += [f'- [[{i["id"]}]] {i["state"].lower()}: {i["title"]}' for i in open_items] or ['- nothing open']
    return '\n'.join(lines) + '\n' + FOOTER


def render_status(meta: dict, counts: dict, settings: dict) -> str:
    scan = meta.get('last_scan') or {}
    lines = [frontmatter({'last_scan': scan.get('finished_at'), 'paused': bool(meta.get('paused'))}), '# Attention status', '']
    for source, value in sorted((scan.get('sources') or {}).items()):
        lines.append(f'- {source}: {value["status"]}' + (f' ({value.get("error_type")})' if value.get('error_type') else ''))
    setup = {'telegram': 'python -m integrations.attention.telegram_user setup',
             'whatsapp': 'python -m integrations.attention.whatsapp pair'}
    lines += [f'- {channel}: not set up ({command})' for channel, command in setup.items()
              if channel not in (scan.get('sources') or {})]
    lines.append('')
    lines += [f'- {label}: {counts[key]}' for key, label in COUNT_LABELS]
    lines += ['', brief.status_line(meta, settings)]
    return '\n'.join(lines) + '\n' + FOOTER


COUNT_LABELS = [('pending_replies', 'Pending replies'), ('open_commitments', 'Open commitments'),
                ('waiting_on_others', 'Waiting on others'), ('appointment_candidates', 'Appointment candidates'),
                ('to_review', 'To confirm'), ('snoozed', 'Snoozed'), ('quiet', 'Older, kept quietly')]


def counts(items: list[dict]) -> dict:
    active = [i for i in items if i['state'] in store.OPEN and not priority.quiet(i)]
    return {'quiet': sum(i['state'] in store.OPEN and priority.quiet(i) for i in items),'pending_replies': sum(i['kind'] == 'reply' for i in active),
            'open_commitments': sum(i['kind'] == 'commitment' for i in active),
            'waiting_on_others': sum(i['kind'] == 'waiting' for i in active),
            'appointment_candidates': sum(i['kind'] == 'appointment' for i in active),
            'to_review': sum(i['review'] for i in active),
            'snoozed': sum(i['state'] == store.SNOOZED for i in items)}


def snapshot(db, now: datetime, settings: dict) -> dict:
    cutoff = store.iso(now - timedelta(days=settings['retain_completed_days']))
    items = [store.row_dict(row) for row in db.execute(
        f'SELECT * FROM items WHERE state NOT IN ({",".join("?" * len(store.CLOSED))}) OR closed_at>=? ORDER BY id',
        (*sorted(store.CLOSED), cutoff))]
    contacts = {row['id']: dict(row) for row in db.execute('SELECT * FROM contacts ORDER BY id')}
    drafts = {row['item_id']: dict(row) for row in db.execute(
        'SELECT * FROM drafts WHERE id IN (SELECT MAX(id) FROM drafts GROUP BY item_id)')}
    meta = {'last_scan': store.meta_get(db, 'last_scan'), 'paused': store.meta_get(db, 'paused', False)}
    return {'items': items, 'contacts': contacts, 'drafts': drafts, 'meta': meta,
            'identities': [dict(r) for r in db.execute('SELECT * FROM identities ORDER BY channel, address')],
            'proposals': [dict(r) for r in db.execute("SELECT * FROM identity_proposals WHERE status='proposed'")]}


def current_brief(data: dict, now: datetime, settings: dict) -> str:
    names = {key: value['name'] for key, value in data['contacts'].items()}
    items = [dict(item, draft=data['drafts'][item['id']]['body']) if item['id'] in data['drafts'] else item
             for item in data['items']]
    return brief.build(items, names, now, settings, brief.status_line(data['meta'], settings))


def files(data: dict, now: datetime, settings: dict) -> dict[str, str]:
    output = {}
    for item in data['items']:
        output[f'{folder(item)}/{item["id"]}.md'] = render_item(
            item, data['contacts'].get(item['contact_id']), data['drafts'].get(item['id']), settings)
    tracked = {item['contact_id'] for item in data['items']}
    for contact_id, contact in data['contacts'].items():
        if contact_id not in tracked:
            continue  # people with nothing tracked would only add noise to the folder
        output[f'contacts/{contact_id}.md'] = render_contact(
            contact, [r for r in data['identities'] if r['contact_id'] == contact_id],
            [r for r in data['proposals'] if r['channel'] + r['address'] in
             {i['channel'] + i['address'] for i in data['identities'] if i['contact_id'] == contact_id}],
            [i for i in data['items'] if i['contact_id'] == contact_id])
    output['briefs/current.md'] = current_brief(data, now, settings) + '\n'
    output['system/status.md'] = render_status(data['meta'], counts(data['items']), settings)
    output['system/schema.md'] = SCHEMA_DOC
    return output


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def write_all(settings: dict | None = None, now: datetime | None = None) -> dict:
    settings = settings or config.load()
    now = now or store.utcnow()
    root = config.home()
    config.save_defaults()
    written = conflicts = removed = 0
    with store.connect() as db:
        output = files(snapshot(db, now, settings), now, settings)
        known = {row['path']: row['sha'] for row in db.execute('SELECT path, sha FROM exports')}
        for relative, content in sorted(output.items()):
            path = root / relative
            current = path.read_text(encoding='utf-8') if path.exists() else None
            if current == content:
                if known.get(relative) != sha(content):
                    db.execute('INSERT OR REPLACE INTO exports VALUES(?,?)', (relative, sha(content)))
                continue
            if current is not None and relative in known and sha(current) != known[relative]:
                keep_conflict(root, path, now)
                conflicts += 1
            atomic(path, content)
            db.execute('INSERT OR REPLACE INTO exports VALUES(?,?)', (relative, sha(content)))
            written += 1
        for relative, digest in known.items():
            if relative in output:
                continue
            path = root / relative
            if path.exists():
                if sha(path.read_text(encoding='utf-8')) != digest:
                    keep_conflict(root, path, now)
                    conflicts += 1
                path.unlink()
                removed += 1
            db.execute('DELETE FROM exports WHERE path=?', (relative,))
    if conflicts:
        log.event('export_conflict', files=conflicts)
    return {'written': written, 'removed': removed, 'conflicts': conflicts}


def keep_conflict(root: Path, path: Path, now: datetime) -> None:
    target = root / 'system' / 'conflicts' / f'{now.strftime("%Y%m%dT%H%M%S")}-{path.name}'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)


def archive_brief(text: str, now: datetime, settings: dict) -> Path:
    local = now.astimezone(settings['tz'])
    path = config.home() / 'briefs' / 'archive' / f'{local.strftime("%Y-%m-%d-%H%M")}.md'
    atomic(path, text + '\n')
    return path
