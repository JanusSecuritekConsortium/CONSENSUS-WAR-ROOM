"""Local diagnostics/explicit execution. Never issues approval grants."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description='AURELIUS agent runtime')
    parser.add_argument('--prompt', help='Explicit operator request; writes pause for host approval')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    from .config import AgentConfig
    try:
        config = AgentConfig.from_env()
        if args.status:
            print(json.dumps({'enabled': config.enabled, 'executor_backend': config.executor_backend,
                              'executor_model_configured': bool(config.executor_model),
                              'background_enabled': config.background_enabled,
                              'scheduled_enabled': config.scheduled_enabled, 'ajax_enabled': False}))
            return 0
        if args.self_test:
            from .contracts import Step, ToolCall, Tool, Impact
            from .adapters import schema
            from .loop import AgentRuntime
            from .registry import ToolRegistry
            from dataclasses import replace
            class Fake:
                def __init__(self): self.calls = 0
                def step(self, messages, tools, timeout):
                    self.calls += 1
                    return Step(call=ToolCall('probe', {})) if self.calls == 1 else Step(text='Probe completed.')
            registry = ToolRegistry()
            registry.register(Tool('probe', 'Offline read probe', schema(), lambda _: {'ok': True}, Impact.READ))
            result = AgentRuntime(Fake(), registry, replace(config, enabled=True)).run('probe')
            if result.status != 'completed' or result.executed_tools != ['probe']:
                raise RuntimeError('Self-test failed')
            print(json.dumps({'self_test': 'pass', 'live_model_calls': 0, 'external_actions': 0}))
            return 0
        if not args.prompt:
            parser.error('Use --status, --self-test or --prompt')
        from integrations.msty.aurelius import AureliusOperator
        result = AureliusOperator().run_agent(args.prompt)
        print(json.dumps(result.as_dict(), ensure_ascii=False))
        return 0 if result.status in {'completed', 'disabled'} else 1
    except Exception as error:
        print(json.dumps({'status': 'degraded', 'error_type': type(error).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
