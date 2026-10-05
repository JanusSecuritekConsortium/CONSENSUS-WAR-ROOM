"""Executor selection is independent of tribunal/monolith model assignment."""
import json
import os
from urllib.parse import urlsplit
from .contracts import Step, ToolCall


class MstyExecutor:
    def __init__(self, model='', client_factory=None):
        self.model = model
        self.client_factory = client_factory

    def step(self, messages, tools, timeout):
        from integrations.msty.aurelius_provider import resolve_aurelius_provider_config
        provider = resolve_aurelius_provider_config()
        if not provider.ready:
            raise RuntimeError('AURELIUS executor provider unavailable')
        endpoint = urlsplit(provider.api_base_url)
        if (endpoint.scheme not in {'http', 'https'} or
            endpoint.hostname not in {'localhost', '127.0.0.1', '::1'} or
            endpoint.username or endpoint.password or endpoint.query or endpoint.fragment):
            raise RuntimeError('AURELIUS tool executor requires a configured loopback provider')
        model = self.model or os.getenv('AURELIUS_MODEL', '')
        if not model or 'ajax' in model.casefold():
            raise RuntimeError('A verified AURELIUS executor model must be configured')
        from openai import OpenAI
        import httpx
        factory = self.client_factory or OpenAI
        # No remapping, mock inference, fallback endpoint or retry of uncertain calls.
        with httpx.Client(follow_redirects=False, trust_env=False, timeout=timeout) as http_client, \
             factory(base_url=provider.api_base_url, api_key=os.getenv('MSTY_API_KEY', 'msty'),
                     timeout=timeout, max_retries=0, http_client=http_client) as client:
            payload = dict(model=model, messages=messages, temperature=0, max_tokens=2048)
            if tools:
                payload['tools'] = [{'type': 'function', 'function': {
                    'name': t['name'], 'description': t['description'], 'parameters': t['inputSchema']}}
                    for t in tools]
                payload['tool_choice'] = 'auto'
            response = client.chat.completions.create(**payload)
        message = response.choices[0].message
        calls = message.tool_calls or []
        if len(calls) > 1:
            raise ValueError('Executor must return at most one tool call')
        if calls:
            function = calls[0].function
            arguments = json.loads(function.arguments)
            if not isinstance(arguments, dict):
                raise ValueError('Executor returned non-object arguments')
            return Step(call=ToolCall(function.name, arguments))
        if not message.content or not message.content.strip():
            raise ValueError('Executor returned no usable response')
        return Step(text=message.content.strip())
