"""Windows Task Scheduler entry point, so the scan and brief run even when Msty Go's scheduler does not.

    pythonw -m integrations.attention.backup scan | brief | briefing morning|evening

Runs without a console. Output goes to <state folder>/system/backup.log, which stays in the vault.
"""
from __future__ import annotations

from datetime import datetime, time
import json
import sys
import traceback

from . import api, config, notifier, scan

LOG_LIMIT = 200_000
# Same windows as the aurelius_publish_briefing MCP tool: a PC that wakes late never sends a stale briefing.
BRIEFING_WINDOWS = {'morning': (time(7, 0), time(10, 0)), 'evening': (time(17, 30), time(20, 30))}


def log(text: str) -> None:
    path = config.home() / 'system' / 'backup.log'
    if path.exists() and path.stat().st_size > LOG_LIMIT:
        path.replace(path.with_suffix('.log.old'))
    with path.open('a', encoding='utf-8') as handle:
        handle.write(f'{datetime.now().isoformat(timespec="seconds")} {text}\n')


def brief() -> dict:
    result = api.current_brief(save=True)
    lines = [line.strip() for line in result['brief'].splitlines() if line.strip()]
    notifier.desktop('Personal attention brief', '\n'.join(lines[1:5]) or 'Nothing needs you today.')
    return {'archived': result['archived'], 'counts': result['counts']}


def briefing(mode: str) -> dict:
    """Publish the Aurelius Telegram briefing; publish() keeps one delivery per day whoever calls it."""
    from integrations.msty.personal.connectors import TZ
    from integrations.msty.personal.publication import publish
    start, end = BRIEFING_WINDOWS[mode]
    if not start <= datetime.now(TZ).time() < end:
        return {'status': 'outside_window'}
    result = publish(mode, send=True)
    return {'status': result.get('status', 'completed')}


def main(argv=None) -> int:
    args = argv or sys.argv[1:] or ['']
    command = args[0]
    if command not in ('scan', 'brief', 'briefing') or (command == 'briefing' and args[1:] not in (['morning'], ['evening'])):
        log(f'unknown command {" ".join(args)!r}')
        return 2
    command = ' '.join(args)
    try:
        result = scan.run() if args[0] == 'scan' else brief() if args[0] == 'brief' else briefing(args[1])
        log(f'{command} ok {json.dumps(result, ensure_ascii=False, default=str)[:400]}')
        return 0
    except Exception as error:  # the log is the only place a windowless run can report
        log(f'{command} failed {type(error).__name__}: {error}\n{traceback.format_exc(limit=3)}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
