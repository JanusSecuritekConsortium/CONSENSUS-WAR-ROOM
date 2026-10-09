import argparse
import json
import sys
from . import store
from .connectors import collect


def main():
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('setup', 'status', 'test', 'review', 'publish'))
    parser.add_argument('--mode', choices=('morning', 'evening', 'weekly'), default='weekly')
    parser.add_argument('--telegram', action='store_true', help='Deliver through the existing Aurelius Telegram recipient')
    parser.add_argument('--edition', help='Explicit corrected publication edition; preserves daily delivery receipts')
    args = parser.parse_args()
    if args.action=='setup':
        from .setup import main as setup
        setup()
    elif args.action=='publish':
        from .publication import publish
        try:
            print(json.dumps(publish(args.mode, send=args.telegram, edition=args.edition), ensure_ascii=False))
        except Exception as error:
            print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
            raise SystemExit(1)
    elif args.action=='review':
        from .review import run
        print(run(mode=args.mode))
    elif args.action=='status':
        print(json.dumps([{'id':a['id'], 'label':a['label'], 'kind':a['kind'], 'enabled':a['enabled']} for a in store.load()['accounts']], indent=2))
    else:
        results = collect(store.load())
        print(json.dumps([{key:value for key,value in r.items() if key not in ('messages','events','files')} for r in results], indent=2))


if __name__ == '__main__':
    main()
