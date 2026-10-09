"""Explicit read-only audit of every source, including disabled sources.

Only status, counts and coverage warnings leave the collectors. No mail bodies,
subjects, calendar events, file names or credentials are printed or persisted.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from . import store
from .connectors import collect
from .status import missing_fields


def check(account):
    missing = missing_fields(account)
    if missing:
        return {'id': account['id'], 'status': 'setup incomplete', 'missing': missing,
                'enabled': account.get('enabled', False)}
    result = collect({'accounts': [dict(account, enabled=True)]})[0]
    summary = {key: value for key, value in result.items() if key not in ('messages', 'events', 'files')}
    summary['counts'] = {key: len(result[key]) for key in ('messages', 'events', 'files') if key in result}
    summary['enabled'] = account.get('enabled', False)
    return summary


def main():
    original = store.load()
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(check, account) for account in original['accounts']]):
            result = future.result()
            results.append(result)
            print(json.dumps(result), flush=True)
    # Re-read before saving so a concurrent setup edit is not overwritten.
    config = store.load()
    snapshots = {account['id']: account for account in original['accounts']}
    by_id = {result['id']: result for result in results}
    for account in config['accounts']:
        result = by_id.get(account['id'])
        if not result or account != snapshots.get(account['id']):
            continue
        if result['status'] == 'setup incomplete':
            for key in ('last_test_at', 'last_test_ok', 'last_test_warnings'):
                account.pop(key, None)
        else:
            account['last_test_at'] = result['checked_at']
            account['last_test_ok'] = result['status'] == 'ok'
            account['last_test_warnings'] = result.get('warnings', [])
    store.save(config)
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'results': results}
    (store.ROOT / 'integration-audit-latest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
