"""Lazy construction: no connections, polling or model discovery at import."""
from .adapters import build_registry
from .config import AgentConfig
from .executor import MstyExecutor
from .loop import AgentRuntime


def build_agent(operator=None, config=None, executor=None, filesystem=None, telegram_sender=None):
    settings = config or AgentConfig.from_env()
    if not settings.enabled:
        return AgentRuntime(executor or MstyExecutor(settings.executor_model), None, settings)
    return AgentRuntime(executor or MstyExecutor(settings.executor_model),
                        build_registry(operator, filesystem, telegram_sender), settings)


def scheduled_report(kind, agent_factory=None):
    """Keep the existing factual collector as the degraded/disabled report path."""
    from integrations.msty.aurelius_reports import collect_report
    if kind not in {'morning', 'evening'}:
        raise ValueError('Unknown report kind')
    try:
        settings = AgentConfig.from_env()
        if settings.enabled and settings.scheduled_enabled:
            from .contracts import Step, ToolCall, Tool, Impact
            from .registry import ToolRegistry
            from .adapters import schema
            import json
            class ReportExecutor:
                def step(self, messages, tools, timeout):
                    if messages[-1]['role'] != 'tool':
                        return Step(call=ToolCall('aurelius_report', {'kind': kind}))
                    evidence = json.loads(messages[-1]['content'])
                    data = json.loads(evidence['data'])
                    if evidence['truncated'] or not isinstance(data.get('body_text'), str):
                        raise ValueError('Incomplete source report')
                    return Step(text=data['body_text'])
            registry = ToolRegistry()
            registry.register(Tool(
                'aurelius_report', 'Collect the factual morning or evening report.',
                schema({'kind': {'type': 'string', 'enum': ['morning', 'evening']}}, ['kind']),
                lambda a: {'body_text': collect_report(a['kind'])}, Impact.READ, 'reports'))
            from dataclasses import replace
            bounded = replace(settings, max_rounds=2, max_tools=1, result_chars=16000,
                              context_chars=max(40000, settings.context_chars))
            agent = agent_factory() if agent_factory else AgentRuntime(ReportExecutor(), registry, bounded)
            from .loop import audit
            audit('scheduled_source', kind=kind)
            result = agent.run('Collect the '+kind+' aurelius report from current source evidence.')
            if result.status != 'completed' or not result.text.strip():
                raise ValueError('Source runtime degraded')
            return result.text
    except Exception as error:
        from .loop import audit
        audit('scheduled_degraded', kind=kind, error_type=type(error).__name__)
    return collect_report(kind)
