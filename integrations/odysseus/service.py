"""Lazy AURELIUS delegation. Scheduled jobs remain with their current owner."""
from .client import OdysseusClient, OdysseusConfig, OdysseusResult
from .evidence import clean, collect


class OdysseusRuntime:
    def __init__(self, config=None, client=None):
        self.config = config or OdysseusConfig.from_env()
        self.client = client or OdysseusClient(self.config)

    def run(self, prompt, evidence=None):
        if not self.config.enabled:
            return OdysseusResult('', 'disabled', '', reason='feature_disabled')
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
            return OdysseusResult('', 'degraded', 'No valid operator input was supplied.', reason='invalid_input')
        # Avoid opening personal sources until configuration and credential are present.
        if not self.config.session_id or not self.config.token_path.is_file():
            return self.client.run(prompt)
        context = {'sources': collect(prompt), 'operator_context': clean(evidence or {})}
        return self.client.run(prompt, evidence=context)

    def status(self):
        return self.client.status()
