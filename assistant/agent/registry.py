from __future__ import annotations

from copy import deepcopy
import re
from jsonschema import Draft202012Validator
from referencing import Registry as SchemaRegistry
from .contracts import Tool, Impact


def _no_remote_reference(uri):
    raise ValueError('Remote schema references are disabled')


class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._validators = {}

    def register(self, tool: Tool):
        if not isinstance(tool.impact, Impact) or not callable(tool.handler) or not isinstance(tool.description, str):
            raise ValueError('Invalid host tool configuration')
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', tool.name) or tool.name in self._tools:
            raise ValueError('Invalid or duplicate tool name')
        if tool.schema.get('type') != 'object':
            raise ValueError('Tool arguments must use an object schema')
        Draft202012Validator.check_schema(tool.schema)
        # Freeze caller-owned metadata so it cannot change after approval.
        from dataclasses import replace
        tool = replace(tool, schema=deepcopy(tool.schema))
        self._tools[tool.name] = tool
        self._validators[tool.name] = Draft202012Validator(
            tool.schema, registry=SchemaRegistry(retrieve=_no_remote_reference))

    def get(self, name):
        if name not in self._tools:
            raise ValueError('Unknown tool')
        return self._tools[name]

    def validate(self, name, arguments):
        self.get(name)
        if not isinstance(arguments, dict):
            raise ValueError('Tool arguments must be an object')
        self._validators[name].validate(arguments)

    def retrieve(self, query, limit=6):
        terms = set(re.findall(r'\w+', query.casefold()))
        def score(tool):
            tokens = set(re.findall(r'\w+', (tool.name.replace('_', ' ') + ' ' +
                         tool.description + ' ' + tool.domain).casefold()))
            return len(terms & tokens)
        return sorted(self._tools.values(), key=lambda t: (-score(t), t.name))[:limit]

    def descriptors(self):
        return [deepcopy(t.descriptor()) for t in self._tools.values()]
