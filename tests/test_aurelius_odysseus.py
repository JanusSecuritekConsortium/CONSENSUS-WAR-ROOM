"""Offline tests of the real-service boundary; no model calls or messages."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from integrations.odysseus.client import OdysseusClient, OdysseusConfig, SessionLock, parse_events
from integrations.odysseus import evidence, mcp_server
from integrations.odysseus.service import OdysseusRuntime


def stream(*events, done=True):
    return ''.join('data: '+json.dumps(event, ensure_ascii=False)+'\n\n' for event in events)+\
        ('data: [DONE]\n\n' if done else '')


class OdysseusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.token = self.directory / 'token.txt'
        self.token.write_text('ody_offline_test_credential', encoding='utf-8')
        self.config = OdysseusConfig(enabled=True, session_id='dedicated-session',
                                    endpoint_id='registered', model='existing-qwen', token_path=self.token)
        self.requests = []
        self.settings_patch = patch('integrations.odysseus.client.SETTINGS_PATH', self.directory / 'settings.json')
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def client(self, body=None, status=200, mime='text/event-stream'):
        def handle(request):
            self.requests.append(request)
            if request.url.path == '/api/health':
                return httpx.Response(200, json={'status': 'ok'})
            if request.url.path == '/api/models':
                return httpx.Response(200, json={'hosts': [], 'items': [
                    {'endpoint_id': 'registered', 'endpoint_name': 'Existing',
                     'models': ['existing-qwen'], 'models_extra': [], 'model_type': 'llm',
                     'url': 'http://localhost:11454/v1/chat/completions'}]})
            if request.url.path == '/api/aurelius/capabilities':
                return httpx.Response(200, json={'protocol_version': 1, 'readonly_investigation': True,
                                                'model_fallbacks': False})
            if request.url.path == '/api/session':
                return httpx.Response(200, json={'id': 'created-session', 'model': 'existing-qwen'})
            return httpx.Response(status, headers={'content-type': mime},
                content=body if body is not None else stream({'delta': 'AURELIUS using real Odysseus.'}))
        client = httpx.Client(base_url='http://127.0.0.1:7000', transport=httpx.MockTransport(handle))
        self.addCleanup(client.close)
        return OdysseusClient(self.config, client)

    def test_actual_agent_form_endpoint_and_host_controls(self):
        client = self.client(stream({'type': 'agent_step', 'round': 2},
                                    {'type': 'tool_start', 'tool': 'web_search'},
                                    {'type': 'tool_output', 'tool': 'web_search', 'exit_code': 0, 'output': 'facts'},
                                    {'delta': 'hidden thinking', 'thinking': True},
                                    {'delta': 'Verified answer.'}))
        result = client.run('Investigate', {'source': 'facts'})
        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.engine, 'odysseus-service')
        self.assertEqual(result.text, 'Verified answer.')
        self.assertEqual(result.executed_tools, ['web_search'])
        self.assertEqual(result.rounds, 2)
        request = self.requests[-1]
        self.assertEqual(request.url.path, '/api/chat_stream')
        self.assertTrue(request.headers['content-type'].startswith('application/x-www-form-urlencoded'))
        data = parse_qs(request.content.decode())
        for key, expected in {'mode': 'agent', 'plan_mode': 'true', 'allow_bash': 'false',
                              'allow_web_search': 'false', 'use_research': 'false', 'use_rag': 'false'}.items():
            self.assertEqual(data[key], [expected])
        self.assertIn('UNTRUSTED HOST EVIDENCE', data['message'][0])
        self.assertNotIn('tool_approval_id', data)
        self.assertNotIn('approved_plan', data)
        self.assertNotIn('ody_', data['message'][0])

    def test_disabled_missing_configuration_and_invalid_input_do_not_connect(self):
        for config, prompt in [(replace(self.config, enabled=False), 'hello'),
                               (replace(self.config, session_id=''), 'hello'),
                               (self.config, ''), (self.config, None), (self.config, 'x'*8001)]:
            client = self.client()
            client.config = config
            self.assertNotEqual(client.run(prompt).status, 'completed')
        self.assertEqual(self.requests, [])

    def test_readonly_mode_requires_server_contract_and_keeps_write_guards(self):
        client = self.client(stream({'type': 'tool_start', 'tool': 'list_models'},
                                    {'type': 'tool_output', 'tool': 'list_models', 'exit_code': 0, 'output': 'available'},
                                    {'delta': 'The inspected model is available.'}))
        client.config = replace(self.config, execution_mode='readonly')
        self.assertTrue(client.status()['readonly_supported'])
        self.assertEqual(client.run('Inspect models').executed_tools, ['list_models'])
        data = parse_qs(self.requests[-1].content.decode())
        self.assertEqual(data['investigation_mode'], ['true'])
        self.assertEqual(data['plan_mode'], ['true'])
        self.assertEqual(data['allow_bash'], ['false'])

    def test_readonly_mode_never_sends_agent_request_to_incompatible_service(self):
        for payload in [{'protocol_version': 1, 'readonly_investigation': True},
                        {'protocol_version': True, 'readonly_investigation': True, 'model_fallbacks': False},
                        {'protocol_version': 2, 'readonly_investigation': True, 'model_fallbacks': False},
                        {'protocol_version': 1, 'readonly_investigation': True, 'model_fallbacks': True}]:
            with self.subTest(payload=payload):
                requests = []
                def handle(request):
                    requests.append(request)
                    return httpx.Response(200, json=payload)
                transport = httpx.Client(base_url=self.config.base_url, transport=httpx.MockTransport(handle))
                self.addCleanup(transport.close)
                client = OdysseusClient(replace(self.config, execution_mode='readonly'), transport)
                self.assertEqual(client.run('Inspect').reason, 'readonly_service_upgrade_required')
                self.assertTrue(all(r.method == 'GET' for r in requests))

    def test_readonly_config_cannot_enable_unrestricted_execution(self):
        for mode in ['execute', 'admin', True, None]:
            with self.assertRaises(ValueError):
                replace(self.config, execution_mode=mode)
        path = self.directory / 'settings.json'
        path.write_text('{"execution_mode":"plan"}')
        self.assertEqual(OdysseusConfig.from_env({'AURELIUS_ODYSSEUS_EXECUTION_MODE': 'readonly'}, path).execution_mode,
                         'readonly')

    def test_tool_start_without_result_cannot_report_execution_success(self):
        result = self.client(stream({'type': 'tool_start', 'tool': 'list_models'},
                                    {'delta': 'I inspected the models.'})).run('Inspect')
        self.assertEqual(result.reason, 'tool_execution_unconfirmed')
        self.assertEqual(result.executed_tools, [])
        self.assertEqual(result.attempted_tools, ['list_models'])
        self.assertNotIn('I inspected', result.text)

    def test_failed_tool_is_visible_but_not_counted_as_executed_successfully(self):
        result = self.client(stream({'type': 'tool_start', 'tool': 'list_models'},
                                    {'type': 'tool_output', 'tool': 'list_models', 'exit_code': 1,
                                     'output': 'private server detail'},
                                    {'delta': 'The inspection was unavailable.'})).run('Inspect')
        self.assertEqual(result.executed_tools, [])
        self.assertEqual(result.tool_results, [{'tool': 'list_models', 'success': False, 'exit_code': 1}])
        self.assertNotIn('private server', json.dumps(result.as_dict()))

    def test_native_read_completion_requires_explicit_success_and_dispatch(self):
        for attempted, success, expected in [(True, True, True), (True, None, False),
                                             (False, True, False), (True, False, False)]:
            with self.subTest(attempted=attempted, success=success):
                events = [{'type': 'tool_start', 'tool': 'list_models'}] if attempted else []
                events += [{'type': 'tool_output', 'tool': 'list_models', 'exit_code': None,
                            'success': success, 'output': 'cogito:latest'}, {'delta': 'Answer.'}]
                client = self.client(stream(*events))
                client.config = replace(client.config, execution_mode='readonly')
                result = client.run('Inspect')
                self.assertEqual(result.executed_tools, ['list_models'] if expected else [])
                self.assertEqual(result.status, 'completed' if expected else 'degraded')

    def test_failed_tool_cannot_complete_even_with_a_success_claim(self):
        result = self.client(stream({'type': 'tool_start', 'tool': 'list_models'},
                                    {'type': 'tool_output', 'tool': 'list_models', 'exit_code': 0,
                                     'success': False}, {'delta': 'Success.'})).run('Inspect')
        self.assertEqual(result.status, 'degraded')
        self.assertEqual(result.reason, 'tool_execution_failed')
        self.assertEqual(result.executed_tools, [])

    def test_missing_credential_does_not_connect(self):
        client = self.client()
        client.config = replace(self.config, token_path=self.directory/'missing')
        self.assertEqual(client.run('hello').reason, 'service_failure')
        self.assertEqual(self.requests, [])

    def test_auth_redirect_wrong_mime_and_incomplete_stream_fail_closed(self):
        for code, mime, body in [(401, 'application/json', '{}'),
                                 (302, 'text/html', ''),
                                 (200, 'text/html', 'login'),
                                 (200, 'text/event-stream', stream({'delta': 'partial'}, done=False))]:
            with self.subTest(code=code, mime=mime):
                result = self.client(body, code, mime).run('hello')
                self.assertEqual(result.status, 'degraded')
                self.assertNotIn('partial', result.text)

    def test_remote_error_limits_and_ajax_fallback_cannot_complete(self):
        for event in [{'error': 'secret raw provider response'}, {'type': 'agent_terminal', 'data': {}},
                      {'type': 'rounds_exhausted'}, {'type': 'budget_exceeded'},
                      {'type': 'fallback', 'answered_by': 'Ajax-9B'}]:
            result = self.client(stream({'delta': 'partial'}, event)).run('hello')
            self.assertEqual(result.status, 'degraded')
            self.assertNotIn('partial', result.text)
            self.assertNotIn('secret raw', json.dumps(result.as_dict()))

    def test_sse_event_error_is_recognized(self):
        body = stream({'delta': 'partial'}, done=False)+'event: error\ndata: {"detail":"failure"}\n\ndata: [DONE]\n\n'
        self.assertEqual(self.client(body).run('hello').reason, 'remote_failure')

    def test_pending_question_cannot_be_automatically_approved(self):
        result = self.client(stream({'type': 'ask_user', 'approval_id': 'private', 'data': 'approve?'})).run('hello')
        self.assertEqual(result.status, 'waiting_for_user')
        self.assertEqual(result.pending['approval_owner'], 'odysseus-ui')
        self.assertNotIn('approval_id', result.pending)
        self.assertEqual(len(self.requests), 1)

    def test_model_catalog_and_session_validate_existing_selection(self):
        client = self.client()
        catalog = client.models()
        self.assertNotIn('url', catalog[0])
        with self.assertRaises(ValueError):
            client.create_session('registered', 'new-or-missing-model')
        self.assertFalse(any(r.url.path == '/api/session' for r in self.requests))
        self.assertEqual(client.create_session('registered', 'existing-qwen'), 'created-session')
        data = parse_qs(self.requests[-1].content.decode())
        self.assertEqual(data['endpoint_id'], ['registered'])
        self.assertEqual(data['endpoint_url'], ['http://localhost:11454/v1/chat/completions'])
        self.assertNotIn('skip_validation', data)
        self.assertNotIn('api_key', data)

    def test_session_route_from_catalog_must_be_loopback_and_chat_only(self):
        for url in ['https://remote.example/v1/chat/completions',
                    'http://localhost:7000/api/tokens',
                    'http://key@localhost:11964/v1/chat/completions',
                    'http://localhost:11964/v1/chat/completions?key=secret']:
            client = self.client()
            with patch.object(client, '_model_catalog', return_value=[{
                    'endpoint_id': 'registered', 'models': ['existing-qwen'], 'url': url}]):
                with self.assertRaises(ValueError):
                    client.create_session('registered', 'existing-qwen')
            self.assertFalse(any(r.url.path == '/api/session' for r in self.requests))

    def test_status_never_discloses_token_and_checks_model(self):
        result = self.client().status()
        self.assertTrue(result['ready'])
        self.assertNotIn('ody_', json.dumps(result))
        client = self.client()
        client.config = replace(self.config, model='missing')
        self.assertFalse(client.status()['ready'])

    def test_local_model_warmup_uses_configured_read_timeout(self):
        client, owned = OdysseusClient(self.config)._http()
        try:
            self.assertTrue(owned)
            self.assertEqual(client.timeout.read, self.config.timeout)
            self.assertEqual(client.timeout.connect, 5)
            self.assertFalse(client.follow_redirects)
            self.assertFalse(client.trust_env)
        finally:
            client.close()

    def test_credential_invalid_format_and_size(self):
        for value in ['ordinary password', 'ody_whitespace\ninside', 'ody_'+'x'*4100]:
            self.token.write_text(value)
            with self.assertRaises(ValueError):
                self.config.token()

    def test_loopback_only_and_ajax_rejected(self):
        for origin in ['http://example.com:7000', 'http://localhost:7000/api',
                       'http://key@localhost:7000', 'http://localhost:7000?token=secret']:
            with self.assertRaises(ValueError):
                replace(self.config, base_url=origin)
        with self.assertRaises(ValueError):
            replace(self.config, model='Ajax-9B')

    def test_configuration_flags_override_saved_state(self):
        path = self.directory/'local.json'
        path.write_text(json.dumps({'enabled': True, 'session_id': 'local', 'model': 'qwen'}))
        config = OdysseusConfig.from_env({'AURELIUS_ODYSSEUS_ENABLED': 'false'}, path)
        self.assertFalse(config.enabled)
        self.assertEqual(config.session_id, 'local')
        with self.assertRaises(ValueError):
            OdysseusConfig.from_env({'AURELIUS_ODYSSEUS_ENABLED': 'maybe'}, path)
        path.write_text('{"allow_shell":true}')
        with self.assertRaises(ValueError):
            OdysseusConfig.from_env({}, path)

    def test_os_session_lock_rejects_another_client_and_recovers(self):
        first = SessionLock(self.config.base_url, self.config.session_id, self.directory)
        second = SessionLock(self.config.base_url, self.config.session_id, self.directory)
        self.assertTrue(first.acquire())
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        self.assertFalse(second.acquire())
        first.close()
        self.assertTrue(second.acquire())

    def test_instance_and_cross_instance_busy_do_not_connect(self):
        client = self.client()
        client._run_lock.acquire()
        self.assertEqual(client.run('hello').reason, 'session_busy')
        client._run_lock.release()
        lock = SessionLock(self.config.base_url, self.config.session_id, self.directory)
        self.assertTrue(lock.acquire())
        self.addCleanup(lock.close)
        self.assertEqual(client.run('hello').reason, 'session_busy')
        self.assertEqual(self.requests, [])

    def test_bounded_sse_and_split_unicode(self):
        data = stream({'delta': 'Español'}, done=False).encode()
        pieces = [data[i:i+1] for i in range(len(data))]
        events = list(parse_events(pieces, time.monotonic(), 20))
        self.assertEqual(json.loads(events[0])['delta'], 'Español')
        with self.assertRaises(TimeoutError):
            list(parse_events([b': heartbeat\n'], time.monotonic()-30, 5))
        with self.assertRaises(ValueError):
            list(parse_events([b'x'*262145], time.monotonic(), 20))
        result = self.client(stream({'delta': 'x'*16001})).run('hello')
        self.assertEqual(result.status, 'degraded')

    def test_evidence_oversize_is_explicitly_omitted(self):
        client = self.client()
        client.run('hello', {'huge': 'x'*7000})
        message = parse_qs(self.requests[-1].content.decode())['message'][0]
        self.assertIn('evidence_exceeds_limit', message)
        self.assertNotIn('x'*7000, message)

    def test_narrow_mcp_dispatch_has_no_writes_or_recursive_agent(self):
        initialized = mcp_server.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                                         'params': {'protocolVersion': '2025-03-26'}})
        self.assertEqual(initialized['result']['protocolVersion'], '2025-03-26')
        listed = mcp_server.dispatch({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
        self.assertEqual({t['name'] for t in listed['result']['tools']},
                         {'mnemosyne_search', 'aurelius_memory_recall', 'aurelius_briefing_memory'})
        for name in ['aurelius_agent_run', 'write_file', 'aurelius_memory_remember', 'telegram_send']:
            result = mcp_server.dispatch({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                                         'params': {'name': name}})
            self.assertIn('error', result)
        self.assertIsNone(mcp_server.dispatch({'jsonrpc': '2.0', 'method': 'notifications/initialized'}))

    def test_mnemosyne_read_does_not_create_or_repair_store(self):
        path = self.directory/'memory.json'
        with patch.object(evidence, 'MEMORY_PATH', path):
            self.assertEqual(evidence.mnemosyne_search({'query': 'test'})['status'], 'unavailable')
            self.assertFalse(path.exists())
            path.write_text('{"decisions":[{"topic":"test","token":"private"}]}')
            result = evidence.mnemosyne_search({'query': 'test'})
            self.assertEqual(result['matches'], [{'topic': 'test'}])
            path.write_text('corrupted')
            with self.assertRaises(ValueError):
                evidence.mnemosyne_search({'query': 'test'})
            self.assertEqual(path.read_text(), 'corrupted')

    def test_context_sources_relevant_only_and_fail_individually(self):
        handler = Mock(side_effect=ValueError('private source error'))
        with patch.dict(evidence.HANDLERS, {'mnemosyne_search': handler}):
            self.assertEqual(evidence.collect('Hello AURELIUS'), {})
            self.assertEqual(evidence.collect('CONSENSUS decision')['mnemosyne_search']['status'], 'unavailable')
        with self.assertRaises(ValueError):
            evidence.query_text({'query': 'x', 'path': 'arbitrary'})

    def test_operator_route_uses_real_engine_and_preserves_default(self):
        from integrations.msty.aurelius import AureliusOperator
        local = Mock()
        operator = AureliusOperator(runtime=local, memory=Mock())
        fake = Mock()
        fake.run.return_value.text = 'actual service'
        operator._odysseus_runtime = fake
        with patch('integrations.odysseus.client.OdysseusConfig.from_env', return_value=self.config):
            self.assertEqual(operator.prepare_user_response('hello'), 'actual service')
        local.send_to_agent.assert_not_called()
        with patch('integrations.odysseus.client.OdysseusConfig.from_env', return_value=replace(self.config, enabled=False)),\
             patch.dict('os.environ', {'AURELIUS_AGENT_ENABLED': 'false'}):
            operator.prepare_user_response('legacy')
        local.send_to_agent.assert_called_once()

    def test_voice_explicit_tribunal_routing_bypasses_odysseus(self):
        from assistant.aurelius_runtime import AureliusRuntime
        engine = Mock()
        engine.config.enabled = True
        tribunal = Mock(return_value={'verdict': 'APPROVED'})
        runtime = AureliusRuntime(agent_runtime=engine, consensus_handler=tribunal)
        runtime.handle_text('proposal', route_to_consensus=True)
        tribunal.assert_called_once_with('proposal')
        engine.run.assert_not_called()

    def test_bot_interactive_route_uses_odysseus_without_touching_schedule(self):
        import importlib.util
        # Load as existing provider tests do, without reading real .env credentials.
        import types
        fake_dotenv = types.SimpleNamespace(load_dotenv=lambda *a, **k: None)
        path = ROOT / '_ARBITER' / 'Bot' / 'aurelius_bot.py'
        spec = importlib.util.spec_from_file_location('odysseus_bot_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'dotenv': fake_dotenv}):
            spec.loader.exec_module(module)
        operator = Mock()
        operator.run_odysseus.return_value.text = 'actual Odysseus'
        module.AGENT_OPERATOR = operator
        with patch('integrations.odysseus.client.OdysseusConfig.from_env', return_value=self.config),\
             patch('assistant.agent.config.AgentConfig.from_env', side_effect=ValueError('unused local config')):
            self.assertEqual(module.call_msty('hello', 'interactive'), 'actual Odysseus')
        operator.run_agent.assert_not_called()
        with patch('assistant.agent.service.scheduled_report', return_value='factual scheduled source'):
            self.assertEqual(module.generate_brief('Morning Brief', scheduled=True), 'factual scheduled source')
        self.assertEqual(operator.run_odysseus.call_count, 1)

    def test_consensus_mcp_exposes_real_engine_without_approval_or_route_override(self):
        from integrations.mcp import consensus_mcp_server as server
        names = {tool['name'] for tool in server.TOOLS}
        self.assertIn('aurelius_odysseus_status', names)
        self.assertIn('aurelius_odysseus_task', names)
        with patch('integrations.odysseus.service.OdysseusRuntime') as runtime:
            runtime.return_value.run.return_value.as_dict.return_value = {
                'engine': 'odysseus-service', 'status': 'completed'}
            result = server.aurelius_odysseus_task({'prompt': 'Investigate'})
            self.assertEqual(result['engine'], 'odysseus-service')
            runtime.return_value.run.assert_called_once_with('Investigate')
            for arguments in [{'prompt': 'x', 'approve': True}, {'prompt': 'x', 'model': 'Ajax'},
                              {'prompt': 'x', 'endpoint': 'remote'}, {'prompt': ''}]:
                with self.assertRaises(ValueError):
                    server.aurelius_odysseus_task(arguments)
        self.assertNotIn('aurelius_odysseus_task', evidence.HANDLERS)


if __name__ == '__main__':
    unittest.main()
