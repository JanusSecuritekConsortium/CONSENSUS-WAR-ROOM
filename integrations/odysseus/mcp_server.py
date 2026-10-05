"""Optional read-only stdio MCP boundary for an authenticated Odysseus UI.

Delegated Odysseus tokens cannot execute privileged MCP tools. The HTTP client
therefore supplies these facts as host evidence; admin UI sessions may register
this service explicitly. No writes, arbitrary paths, shell or recursive agents.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from integrations.odysseus.evidence import HANDLERS

TOOLS = [
    {'name': name, 'description': description,
     'inputSchema': {'type': 'object', 'properties': properties, 'additionalProperties': False},
     'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False}}
    for name, description, properties in [
        ('mnemosyne_search', 'Search existing CONSENSUS decision memory.',
         {'query': {'type': 'string', 'maxLength': 200}}),
        ('aurelius_memory_recall', 'Recall relevant facts from the native AURELIUS shared memory pack.',
         {'query': {'type': 'string', 'maxLength': 200}}),
        ('aurelius_briefing_memory', 'Read an archived briefing, which may be stale.',
         {'mode': {'type': 'string', 'enum': ['latest', 'morning', 'evening', 'weekly']}}),
    ]
]


def dispatch(request):
    if not isinstance(request, dict) or request.get('jsonrpc') != '2.0':
        return {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'Invalid request'}}
    if 'id' not in request:
        return None
    reply = {'jsonrpc': '2.0', 'id': request['id']}
    method = request.get('method')
    params = request.get('params', {})
    if not isinstance(params, dict):
        return {**reply, 'error': {'code': -32602, 'message': 'Invalid params'}}
    if method == 'initialize':
        requested = params.get('protocolVersion')
        version = requested if requested in {'2024-11-05', '2025-03-26', '2025-06-18'} else '2024-11-05'
        return {**reply, 'result': {'protocolVersion': version, 'capabilities': {'tools': {}},
                                  'serverInfo': {'name': 'aurelius-consensus-readonly', 'version': '1.0.0'}}}
    if method == 'ping':
        return {**reply, 'result': {}}
    if method == 'tools/list':
        return {**reply, 'result': {'tools': TOOLS}}
    if method == 'tools/call':
        name = params.get('name')
        if not isinstance(name, str) or name not in HANDLERS:
            return {**reply, 'error': {'code': -32602, 'message': 'Read-only tool not found'}}
        try:
            data = HANDLERS[name](params.get('arguments', {}))
            content = json.dumps(data, ensure_ascii=False)
            if len(content) > 20000:
                content = json.dumps({'status': 'source_exceeds_read_budget', 'data_omitted': True})
            return {**reply, 'result': {'content': [{'type': 'text', 'text': content}], 'isError': False}}
        except Exception as error:
            return {**reply, 'result': {'content': [{'type': 'text', 'text': type(error).__name__}], 'isError': True}}
    return {**reply, 'error': {'code': -32601, 'message': 'Method not found'}}


def main():
    while True:
        line = sys.stdin.buffer.readline(262145)
        if not line:
            break
        if len(line) > 262144:
            break
        try:
            response = dispatch(json.loads(line))
        except (ValueError, UnicodeError):
            response = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON'}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
