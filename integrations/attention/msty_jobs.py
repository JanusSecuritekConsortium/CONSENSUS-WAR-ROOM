"""Install the attention schedule as Msty Go scheduled jobs (Msty Go must be closed).

    python -m integrations.attention.msty_jobs            # show what would change
    python -m integrations.attention.msty_jobs --apply    # back up the database, then write
    python -m integrations.attention.msty_jobs --remove --apply

The jobs call tools on the existing CONSENSUS MCP connection: a quiet scan every
30 minutes and the attention brief at the configured times, delivered in Msty Go only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess

from . import config

PREFIX = 'attention-'
SERVER_NAME = 'CONSENSUS MCP'


def database_path() -> Path:
    return Path(os.path.expandvars(r'%APPDATA%\Msty Go\msty-go.db'))


def msty_running() -> bool:
    output = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq MstyGo.exe', '/NH'], capture_output=True, text=True).stdout
    return 'MstyGo.exe' in output


def jobs(settings: dict) -> list[dict]:
    every = int(settings['scan_every_minutes'])
    planned = [{'id': PREFIX + 'scan', 'label': 'Personal attention scan', 'cron': f'*/{every} * * * *',
                'tool': 'attention_scan', 'arguments': {}, 'destinations': [],
                'instructions': 'The source already scanned. Report only its status field in one short line. '
                                'Never call other tools.'}]
    for value in settings['brief_times']:
        hour, minute = map(int, value.split(':'))
        planned.append({'id': f'{PREFIX}brief-{hour:02d}{minute:02d}', 'label': f'Personal attention brief {value}',
                        'cron': f'{minute} {hour} * * *', 'tool': 'attention_brief', 'arguments': {'archive': True},
                        'destinations': ['in_app', 'desktop_notification'],
                        'instructions': 'Repeat the "brief" text from the source exactly, without adding, removing or '
                                        'reordering anything. Never call other tools and never send messages.'})
    return planned


def next_run(cron: str, settings: dict, now: datetime | None = None) -> str:
    """First run time for the two cron shapes used here: */N minutes, or a daily minute and hour."""
    now = (now or datetime.now(timezone.utc)).astimezone(settings['tz']).replace(second=0, microsecond=0)
    minute, hour = cron.split()[:2]
    if minute.startswith('*/'):
        step = int(minute[2:])
        due = now + timedelta(minutes=step - now.minute % step)
    else:
        due = now.replace(hour=int(hour), minute=int(minute))
        if due <= now:
            due += timedelta(days=1)
    return due.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def plan(db, settings: dict) -> dict:
    server = db.execute('SELECT id FROM mcp_servers WHERE name=? AND enabled=1', (SERVER_NAME,)).fetchone()
    if not server:
        raise RuntimeError(f'{SERVER_NAME} is not connected in Msty Go')
    templates = [(json.loads(p), json.loads(q)) for p, q in db.execute(
        'SELECT payload_json, policy_json FROM scheduled_jobs ORDER BY created_at')]
    template = next((t for t in templates if t[0].get('contextSourceServerId') == server[0]
                     and t[0].get('providerId')), None)
    if not template:
        raise RuntimeError('No existing source job to copy the local model settings from')
    payload, policy = template
    provider = db.execute('SELECT base_url FROM providers WHERE id=?', (payload['providerId'],)).fetchone()
    config.loopback(provider[0] if provider and provider[0] else '')  # jobs must use the local model
    return {'server_id': server[0], 'payload': payload, 'policy': policy}


def install(apply: bool, remove: bool = False) -> list[str]:
    settings = config.load()
    path = database_path()
    if apply and msty_running():
        raise RuntimeError('Close Msty Go first (also from the tray); it keeps its database open')
    lines = []
    with sqlite3.connect(path if apply else f'file:{path}?mode=ro', uri=not apply, timeout=15) as db:
        existing = [row[0] for row in db.execute('SELECT id FROM scheduled_jobs WHERE id LIKE ?', (PREFIX + '%',))]
        if remove:
            lines += [f'remove {job_id}' for job_id in existing]
        else:
            context = plan(db, settings)
            for job in jobs(settings):
                lines.append(f'{"update" if job["id"] in existing else "add"} {job["id"]}: {job["label"]} '
                             f'[{job["cron"]}] -> {job["tool"]} -> {", ".join(job["destinations"]) or "no delivery"}')
        if not apply:
            return lines
        backup = Path(r'G:\Msty\Msty Go\Backups') / f'before-attention-jobs-{datetime.now():%Y%m%d-%H%M%S}.db'
        backup.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(backup) as target:
            db.backup(target)
        lines.append(f'backup {backup}')
        with db:
            db.execute('DELETE FROM scheduled_job_destinations WHERE job_id LIKE ?', (PREFIX + '%',))
            db.execute('DELETE FROM scheduled_jobs WHERE id LIKE ?', (PREFIX + '%',))
            if not remove:
                for job in jobs(settings):
                    payload = dict(context['payload'], taskType='reminder', reminderMode='source', message=job['label'],
                                   details='', workspacePath=None, dataProtectionEnabled=False,
                                   contextSourceServerId=context['server_id'], contextSourceToolName=job['tool'],
                                   contextSourceArguments=job['arguments'], contextInstructions=job['instructions'],
                                   agentInstructions='', allowShellAccess=False, allowWebAccess=False, allowWebSearch=False)
                    policy = dict(context['policy'], maxConcurrentRuns=1, notifyOnSuccess=False,
                                  notifyOnFailure=job['tool'] != 'attention_scan', writePolicy='never')
                    db.execute('INSERT INTO scheduled_jobs(id,label,job_kind,resource_kind,trigger_kind,cron_expression,'
                               'timezone,payload_json,policy_json,enabled,next_run_at) VALUES(?,?,?,?,?,?,?,?,?,1,?)',
                               (job['id'], job['label'], 'prompt', 'task', 'cron', job['cron'], settings['timezone'],
                                json.dumps(payload), json.dumps(policy), next_run(job['cron'], settings)))
                    for position, kind in enumerate(job['destinations']):
                        db.execute('INSERT INTO scheduled_job_destinations(id,job_id,kind,config_json,enabled,position,'
                                   "created_at,updated_at) VALUES(?,?,?,'{}',1,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'),"
                                   "strftime('%Y-%m-%dT%H:%M:%fZ','now'))", (f'{job["id"]}-{kind}', job['id'], kind, position))
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Msty Go database integrity check failed; restore the backup')
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--remove', action='store_true')
    args = parser.parse_args()
    for line in install(args.apply, args.remove):
        print(line)
    if not args.apply:
        print('(dry run; nothing changed)')


if __name__ == '__main__':
    main()
