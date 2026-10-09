"""Adapters to actual CONSENSUS components; optional integrations are host-owned."""
from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4
from .contracts import Tool, Impact


def schema(properties=None, required=()):
    return {'type': 'object', 'properties': properties or {},
            'required': list(required), 'additionalProperties': False}


def text(limit=2000):
    return {'type': 'string', 'minLength': 1, 'maxLength': limit}


class Filesystem:
    """Explicit roots only; no shell, executables, credentials or arbitrary paths."""
    def __init__(self, read_root, write_root=None):
        self.read_root = Path(read_root).resolve()
        self.write_root = Path(write_root).resolve() if write_root else None

    def _path(self, root, value):
        if root is None:
            raise ValueError('Filesystem capability unavailable')
        relative = Path(value)
        if relative.is_absolute() or '..' in relative.parts or ':' in value:
            raise ValueError('A relative confined path is required')
        if any(p.startswith('.') or p.casefold() in {'memory', 'logs', 'cache', 'secrets',
               'credentials', 'venv', 'node_modules', '_arbiter'} for p in relative.parts):
            raise ValueError('Sensitive/runtime path is unavailable')
        if re.search(r'credential|secret|password|token|api[-_]?key', relative.name, re.I):
            raise ValueError('Sensitive file is unavailable')
        result = (root / relative).resolve()
        result.relative_to(root)
        if result.suffix.casefold() not in {'.md', '.txt', '.json', '.csv', '.py', '.toml', '.yaml', '.yml'}:
            raise ValueError('Unsupported text file')
        return result

    def read(self, args):
        path = self._path(self.read_root, args['path'])
        if path.stat().st_size > 100000:
            raise ValueError('File exceeds read budget')
        content = path.read_text(encoding='utf-8')
        from integrations.mcp.consensus_mcp_server import redact_text
        redacted = redact_text(content)
        redacted = re.sub(r'''(?i)(\b(?:api[_-]?key|bot[_-]?token|access[_-]?token|password|secret|auth[_-]?token)\b["']?\s*[:=]\s*)[^\r\n,;]+''',
                          r'\1<REDACTED>', redacted)
        return {'path': args['path'], 'content': redacted, 'trust': 'untrusted_data'}

    def write(self, args):
        path = self._path(self.write_root, args['path'])
        if path.suffix.casefold() not in {'.md', '.txt', '.json', '.csv'}:
            raise ValueError('Only report/data files can be written')
        # Refuse overwrites; an approved action creates a new report atomically.
        if path.exists():
            raise FileExistsError('Refusing to overwrite an existing report')
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name('.'+path.name+'.'+uuid4().hex+'.tmp')
        try:
            tmp.write_text(args['content'], encoding='utf-8')
            # Hard-link creation is atomic and fails if a concurrent writer owns the name.
            import os
            os.link(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        return {'saved': True, 'path': args['path']}


def build_registry(operator=None, filesystem=None, telegram_sender=None):
    from .registry import ToolRegistry
    registry = ToolRegistry()
    if operator is not None:
        def search(args):
            # MemoryStore.load can relocate corrupt files. A read tool must not do so.
            path = operator.memory.path
            data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            words = args.get('query', '').casefold().split()
            decisions = data.get('decisions', [])
            return {'matches': [d for d in decisions if all(w in str(d).casefold() for w in words)][-20:],
                    'source': 'core.memory.MemoryStore', 'trust': 'untrusted_data'}
        registry.register(Tool('mnemosyne_search', 'Search remembered CONSENSUS decision analysis memory.',
            schema({'query': {'type': 'string', 'maxLength': 200}}), search, Impact.READ, 'memory'))
        registry.register(Tool('consensus_request', 'Submit a proposal to the existing CONSENSUS tribunal for reasoning; persists a decision.',
            schema({'proposal': text(8000)}, ['proposal']),
            lambda a: operator.submit_proposal_to_arbiter(a['proposal']), Impact.HIGH, 'consensus'))
    # Narrow local tools, excluding the composite action tool (risk varies by operation).
    from integrations.mcp import consensus_mcp_server as server
    allowed = {
        'aurelius_memory_recall': Impact.READ,
        'aurelius_memory_remember': Impact.HIGH,  # native pack requires user-confirmed facts
        'aurelius_memory_forget': Impact.HIGH,
        'aurelius_report': Impact.READ,
        'aurelius_briefing_memory': Impact.READ,
    }
    for descriptor in server.TOOLS:
        name = descriptor['name']
        if name in allowed:
            registry.register(Tool(name, descriptor['description'], descriptor['inputSchema'],
                server.TOOL_HANDLERS[name], allowed[name], 'memory' if 'memory' in name else 'reports'))
    if filesystem:
        registry.register(Tool('read_file', 'Read a bounded text file from the configured project root.',
            schema({'path': text(240)}, ['path']), filesystem.read, Impact.READ, 'filesystem'))
        if filesystem.write_root:
            registry.register(Tool('write_file', 'Create a new report/data file under the configured output root.',
                schema({'path': text(240), 'content': text(12000)}, ['path', 'content']),
                filesystem.write, Impact.WRITE, 'filesystem', False))
    if telegram_sender:
        def send(args):
            if not telegram_sender(args['text']):
                raise RuntimeError('Telegram outcome not verified')
            return {'delivered': True}
        registry.register(Tool('telegram_send', 'Send exact text to the existing host-configured Telegram recipient.',
            schema({'text': text(4000)}, ['text']), send, Impact.HIGH, 'communication', False))
    return registry
