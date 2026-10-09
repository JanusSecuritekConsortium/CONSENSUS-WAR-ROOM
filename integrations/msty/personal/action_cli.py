"""Absolute-path entry point for hosts that do not expose MCP tools to agents."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from integrations.msty.personal.action_tools import handle


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--accounts', action='store_true')
    group.add_argument('--request-file', type=Path)
    args = parser.parse_args()
    request = {'operation': 'accounts'} if args.accounts else json.loads(
        args.request_file.read_text(encoding='utf-8-sig'))
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(handle(request), ensure_ascii=False))


if __name__ == '__main__':
    main()
