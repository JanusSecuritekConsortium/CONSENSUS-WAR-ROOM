"""Authenticated loopback MCP client for the existing Msty Go agent."""
import json
from urllib.parse import urlsplit
import requests
from . import store


def connection_config():
    config = store.secret_read('msty-local-mcp')
    parsed = urlsplit(config.get('url', ''))
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Configure the loopback Msty Go MCP URL')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Invalid local MCP URL')
    if not config.get('token'):
        raise ValueError('Configure the local MCP bearer token')
    return config


class Client:
    def __init__(self, config=None):
        self.config = config or connection_config()
        self.session = requests.Session()
        self.headers = {'Authorization': 'Bearer ' + self.config['token'],
                        'Accept': 'application/json, text/event-stream',
                        'MCP-Protocol-Version': '2025-03-26'}
        self.counter = 0

    def request(self, method, params=None):
        self.counter += 1
        try:
            response = self.session.post(self.config['url'], headers=self.headers,
                json={'jsonrpc':'2.0', 'id':self.counter, 'method':method, 'params':params or {}},
                timeout=(5, 40), allow_redirects=False)
            response.raise_for_status()
            if response.headers.get('Mcp-Session-Id'):
                self.headers['Mcp-Session-Id'] = response.headers['Mcp-Session-Id']
            if 'text/event-stream' in response.headers.get('Content-Type', ''):
                values = [json.loads(line[5:].strip()) for line in response.text.splitlines()
                          if line.startswith('data:') and line[5:].strip()]
                result = next(item for item in values if item.get('id') == self.counter)
            else:
                result = response.json()
            if result.get('error'):
                raise RuntimeError('Msty MCP rejected the request')
            return result['result']
        except Exception:
            raise RuntimeError('Local Msty MCP request failed; check its endpoint and authorization') from None

    def initialize(self):
        return self.request('initialize', {'protocolVersion':'2025-03-26', 'capabilities':{},
                           'clientInfo':{'name':'Aurelius voice relay','version':'1.0'}})

    def tools(self):
        return self.request('tools/list')['tools']

    def call(self, name, arguments):
        result = self.request('tools/call', {'name':name, 'arguments':arguments})
        if result.get('isError'):
            raise RuntimeError('Msty tool did not accept the request')
        return result

    def close(self):
        self.session.close()
