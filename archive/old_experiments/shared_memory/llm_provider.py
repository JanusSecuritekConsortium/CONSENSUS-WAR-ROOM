class LLMProvider:
    def call(self, model, prompt, system_prompt, config):
        raise NotImplementedError("LLMProvider subclasses must implement call().")

class OllamaProvider(LLMProvider):
    def call(self, model, prompt, system_prompt, config):
        import requests
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stop": config.stop_tokens or []
            },
            timeout=config.timeout_seconds
        )
        response.raise_for_status()
        return response.json()["response"]

class LLMProviderFactory:
    @staticmethod
    def get_provider(engine: str) -> LLMProvider:
        providers = {
            "ollama": OllamaProvider
            # Add others like "openai": OpenAIProvider, etc.
        }
        return providers.get(engine.lower(), OllamaProvider)()
