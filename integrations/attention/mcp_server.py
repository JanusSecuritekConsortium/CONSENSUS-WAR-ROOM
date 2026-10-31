"""Standalone stdio MCP server exposing every attention tool to any local MCP host."""
from __future__ import annotations

import json
import sys

from . import tools

PROTOCOL = '2024-11-05'


def handle(message: dict) -> dict | None:
    method, request_id = message.get('method'), message.get('id')
    try:
        if method == 'initialize':
            result = {'protocolVersion': PROTOCOL, 'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': 'Personal Attention', 'version': '1.0'}}
        elif method == 'tools/list':
            result = {'tools': tools.TOOLS}
        elif method == 'tools/call':
            params = message.get('params') or {}
            data = tools.call(str(params.get('name')), params.get('arguments') or {})
            result = {'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False, default=str)}]}
        elif method in ('resources/list', 'prompts/list'):
            result = {method.split('/')[0]: []}
        elif method and method.startswith('notifications/'):
            return None
        else:
            raise ValueError(f'Unsupported method: {method}')
        return {'jsonrpc': '2.0', 'id': request_id, 'result': result}
    except Exception as error:
        return {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32000, 'message': str(error)[:500]}}


def serve() -> None:
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = handle(json.loads(line))
        except ValueError as error:
            response = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': str(error)}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    serve()
