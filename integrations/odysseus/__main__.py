from __future__ import annotations

import argparse
from dataclasses import replace
import json

from .client import OdysseusClient, OdysseusConfig, SETTINGS_PATH
from .service import OdysseusRuntime


def main():
    parser = argparse.ArgumentParser(description='Connect real Odysseus to AURELIUS over its public API.')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    commands.add_parser('models')
    setup = commands.add_parser('setup')
    setup.add_argument('--endpoint-id', required=True)
    setup.add_argument('--model', required=True)
    ask = commands.add_parser('ask')
    ask.add_argument('prompt')
    args = parser.parse_args()
    try:
        config = OdysseusConfig.from_env()
        client = OdysseusClient(config)
        if args.command == 'status':
            result = client.status()
        elif args.command == 'models':
            result = client.models()
        elif args.command == 'setup':
            if SETTINGS_PATH.exists():
                raise FileExistsError('An Odysseus session is already configured')
            selected = replace(config, model=args.model, endpoint_id=args.endpoint_id)
            session = OdysseusClient(selected).create_session(args.endpoint_id, args.model)
            data = {'enabled': True, 'base_url': config.base_url, 'session_id': session,
                    'model': args.model, 'endpoint_id': args.endpoint_id,
                    'allow_web': config.allow_web, 'timeout': config.timeout}
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation prevents replacing a live session or racing another setup.
            with SETTINGS_PATH.open('x', encoding='utf-8') as handle:
                json.dump(data, handle, indent=2)
            result = {'configured': True, 'engine': 'odysseus-service', 'session_id': session,
                      'model': args.model, 'mode': 'investigation'}
        else:
            result = OdysseusRuntime(config, client).run(args.prompt).as_dict()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        # Never print exception bodies that might include request headers or provider details.
        print(json.dumps({'configured': False, 'error_type': type(error).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
