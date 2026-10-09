"""MCP client boundary: explicit host connections, stdio or injected JSON-RPC."""
from __future__ import annotations

import json
import os
import queue
import subprocess
from threading import Lock, Thread
from time import monotonic
from .contracts import Tool, Impact


class StdioTransport:
    def __init__(self, command: list[str], cwd=None, timeout=15.0):
        if not command or not all(isinstance(item, str) for item in command):
            raise ValueError('Host must supply a command argument list')
        self.timeout = timeout
        self._lock = Lock()
        self._responses = queue.Queue(maxsize=64)
        self._closed = False
        self._process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self._reader = Thread(target=self._read, daemon=True, name='aurelius-mcp-reader')
        self._reader.start()

    def _read(self):
        try:
            while not self._closed:
                line = self._process.stdout.readline(1_000_001)
                if not line:
                    raise EOFError('MCP server closed')
                if len(line) > 1_000_000 or not line.endswith(b'\n'):
                    raise ValueError('Oversized MCP response')
                self._responses.put_nowait(json.loads(line.decode('utf-8')))
        except Exception:
            try:
                self._responses.put_nowait({'transport_failure': True})
            except queue.Full:
                pass

    def __call__(self, message):
        with self._lock:
            if self._closed:
                raise RuntimeError('MCP transport closed')
            raw = (json.dumps(message, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
            if len(raw) > 1_000_000:
                raise ValueError('Oversized MCP request')
            try:
                self._process.stdin.write(raw)
                self._process.stdin.flush()
                if 'id' not in message:
                    return None
                until = monotonic() + self.timeout
                while True:
                    response = self._responses.get(timeout=max(0.001, until - monotonic()))
                    if response.get('transport_failure'):
                        raise RuntimeError('MCP transport failed')
                    if response.get('id') == message['id'] and ('result' in response or 'error' in response):
                        return response
                    if 'id' in response and 'method' in response:
                        # Sampling, elicitation and server requests cannot acquire host privileges.
                        rejection = {'jsonrpc': '2.0', 'id': response['id'],
                                     'error': {'code': -32601, 'message': 'Client capability unavailable'}}
                        self._process.stdin.write((json.dumps(rejection)+'\n').encode('utf-8'))
                        self._process.stdin.flush()
                    if monotonic() >= until:
                        raise TimeoutError('MCP response deadline')
            except Exception:
                self.close()
                raise

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
        self._reader.join(timeout=2)
        self._process.stdin.close()
        self._process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class MCPConnection:
    def __init__(self, transport):
        self.transport = transport
        self._id = 0
        self._lock = Lock()
        self.version = None

    def request(self, method, params):
        with self._lock:
            self._id += 1
            response = self.transport({'jsonrpc': '2.0', 'id': self._id, 'method': method, 'params': params})
            if not isinstance(response, dict) or response.get('jsonrpc') != '2.0' or response.get('id') != self._id:
                raise ValueError('Invalid MCP response envelope')
            if 'error' in response or 'result' not in response:
                raise RuntimeError('MCP request failed')
            return response['result']

    def initialize(self):
        result = self.request('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                              'clientInfo': {'name': 'CONSENSUS AURELIUS', 'version': '1.0'}})
        self.version = result.get('protocolVersion')
        if self.version not in {'2024-11-05', '2025-03-26', '2025-06-18'}:
            raise ValueError('Unsupported MCP protocol version')
        if not isinstance(result.get('capabilities', {}).get('tools'), dict):
            raise ValueError('MCP server has no tools capability')
        self.transport({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def discover(self):
        if self.version is None:
            self.initialize()
        tools, cursors, cursor = [], set(), None
        for _ in range(10):
            result = self.request('tools/list', {'cursor': cursor} if cursor else {})
            page = result.get('tools')
            if not isinstance(page, list) or len(tools) + len(page) > 256:
                raise ValueError('Invalid or excessive MCP tool catalog')
            tools.extend(page)
            cursor = result.get('nextCursor')
            if not cursor:
                return tools
            if not isinstance(cursor, str) or cursor in cursors:
                raise ValueError('Invalid MCP pagination')
            cursors.add(cursor)
        raise ValueError('MCP catalog page limit')

    def call(self, name, arguments):
        result = self.request('tools/call', {'name': name, 'arguments': arguments})
        if not isinstance(result, dict) or result.get('isError'):
            raise RuntimeError('MCP tool returned an error')
        return result

    def register(self, registry, namespace, impacts=None):
        """Risk mappings come from host configuration, never server annotations."""
        impacts = impacts or {}
        catalog = self.discover()
        pending = []
        for descriptor in catalog:
            name = descriptor['name']
            pending.append(Tool(name=namespace+'_'+name,
                description=str(descriptor.get('description', 'MCP tool'))[:2000],
                schema=descriptor['inputSchema'], handler=lambda args, n=name: self.call(n, args),
                impact=Impact(impacts.get(name, Impact.HIGH)), domain=namespace, untrusted=True))
        # Validate the entire catalog before changing the target registry.
        from .registry import ToolRegistry
        validation = ToolRegistry()
        existing = {t['name'] for t in registry.descriptors()}
        for tool in pending:
            if tool.name in existing:
                raise ValueError('MCP tool collision')
            validation.register(tool)
        for tool in pending:
            registry.register(tool)
        return len(pending)
