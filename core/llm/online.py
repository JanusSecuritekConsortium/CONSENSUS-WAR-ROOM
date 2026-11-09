"""Online models for tribunal voters: Anthropic (Claude), OpenAI (GPT/Codex) and DeepSeek.

A voter goes online only when the operator names a model for it, for example in the
gitignored `.env` file beside the code:

    CONSENSUS_ONLINE_MODEL_RATIONALIS=anthropic:claude-sonnet-5-5
    CONSENSUS_ONLINE_MODEL_BELLATOR=deepseek:deepseek-chat
    ANTHROPIC_API_KEY=...
    DEEPSEEK_API_KEY=...

Without a model name or a key the voter stays on its local model. A failed online call is
logged and the voter falls back to its local model. API keys are read here and sent only in
the provider's own request header; they never appear in logs, errors or results.
"""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import httpx

from config.names import TRIBUNAL_AGENT_IDS
from core.llm.backends import ProviderRequestError

ENV_PREFIX = "CONSENSUS_ONLINE_MODEL_"
DEFAULT_TOKEN_BUDGET = 250_000
# Reasoning models spend output tokens before they answer; the local 900-token limit is too small online.
MIN_OUTPUT_TOKENS = 4000
DEFAULT_TIMEOUT_SECONDS = 180.0


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    base_url: str
    key_env: str
    api: str  # "anthropic" or "openai"


PROVIDERS: Dict[str, Provider] = {
    "anthropic": Provider("anthropic", "Claude (Anthropic)", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "anthropic"),
    "openai": Provider("openai", "OpenAI (GPT / Codex)", "https://api.openai.com/v1", "OPENAI_API_KEY", "openai"),
    "deepseek": Provider("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "openai"),
}


@dataclass(frozen=True)
class OnlineRoute:
    agent_id: str
    provider: Provider
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider.name}:{self.model}"

    @property
    def backend(self) -> str:
        return f"online:{self.provider.name}"


@dataclass(frozen=True)
class OnlineResult:
    text: str
    input_tokens: int
    output_tokens: int


class OnlineModelError(ProviderRequestError):
    """An online call failed. The message never contains the API key."""


# ---- settings ---------------------------------------------------------------------------------

_env_file_cache: Dict[str, Any] = {"path": None, "mtime": None, "values": {}}


def _env_file() -> Optional[Path]:
    configured = os.environ.get("CONSENSUS_ONLINE_ENV_FILE")
    if configured is not None:
        return Path(configured) if configured.strip() else None
    from core.paths import SYSTEM_ROOT, is_frozen_runtime
    # The packaged CONSENSUS.exe runs from dist\; its settings live in the source folder above it.
    if is_frozen_runtime() and not (SYSTEM_ROOT / ".env").is_file():
        return SYSTEM_ROOT.parent / ".env"
    return SYSTEM_ROOT / ".env"


def _file_values() -> Dict[str, str]:
    path = _env_file()
    if path is None or not path.is_file():
        return {}
    mtime = path.stat().st_mtime
    if _env_file_cache["path"] != path or _env_file_cache["mtime"] != mtime:
        try:
            from dotenv import dotenv_values
            values = {key: value for key, value in dotenv_values(path).items() if value is not None}
        except Exception:
            values = {}
        _env_file_cache.update(path=path, mtime=mtime, values=values)
    return _env_file_cache["values"]


def setting(name: str, default: str = "") -> str:
    """The process environment wins over the .env file, so one run can override a stored choice."""
    value = os.environ.get(name)
    if value is None:
        value = _file_values().get(name)
    return default if value is None else str(value).strip()


def _flag(name: str, default: bool) -> bool:
    value = setting(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def online_enabled() -> bool:
    return _flag("CONSENSUS_ONLINE_MODELS", True)


def share_personal_context() -> bool:
    """Personal vault context stays local unless the operator explicitly allows it."""
    return _flag("CONSENSUS_ONLINE_SHARE_PERSONAL", False)


def token_budget() -> int:
    try:
        return max(0, int(setting("CONSENSUS_ONLINE_TOKEN_BUDGET", str(DEFAULT_TOKEN_BUDGET))))
    except ValueError:
        return DEFAULT_TOKEN_BUDGET


def _api_key(provider: Provider) -> str:
    return setting(provider.key_env)


def parse_route(agent_id: str, value: str) -> Optional[OnlineRoute]:
    provider_name, _, model = value.partition(":")
    provider = PROVIDERS.get(provider_name.strip().lower())
    model = model.strip()
    if provider is None or not model:
        return None
    return OnlineRoute(agent_id, provider, model)


def configured_route(agent_id: str) -> Optional[OnlineRoute]:
    """The online model named for this voter, whether or not its key is present."""
    agent_id = agent_id.upper()
    if agent_id not in TRIBUNAL_AGENT_IDS or not online_enabled():
        return None
    value = setting(ENV_PREFIX + agent_id)
    return parse_route(agent_id, value) if value else None


def route_for(agent_id: str) -> Optional[OnlineRoute]:
    """The online model this voter will try first, or None when it stays local."""
    route = configured_route(agent_id)
    if route is None or not _api_key(route.provider):
        return None
    return route


def status_report() -> list[Dict[str, Any]]:
    """Per voter: the configured online model and whether its key is present. Never the key itself."""
    rows = []
    for agent_id in TRIBUNAL_AGENT_IDS:
        raw = setting(ENV_PREFIX + agent_id)
        route = configured_route(agent_id)
        if not raw:
            state = "local"
        elif route is None:
            state = "disabled" if not online_enabled() else "invalid setting"
        elif not _api_key(route.provider):
            state = f"no key ({route.provider.key_env})"
        else:
            state = "online"
        rows.append({"agent_id": agent_id, "setting": raw, "model": route.label if route else "", "state": state})
    return rows


def strip_personal_context(context: Dict[str, Any]) -> bool:
    """Remove the owner's vault brief from a voter context before it is sent online."""
    memory = context.get("memory_context")
    if not isinstance(memory, dict) or "second_brain" not in memory:
        return False
    memory.pop("second_brain", None)
    memory["second_brain_withheld"] = "Personal context is not shared with online models."
    return True


# ---- requests ---------------------------------------------------------------------------------

Poster = Callable[[str, Dict[str, str], Dict[str, Any], float], httpx.Response]


def _post(url: str, headers: Dict[str, str], body: Dict[str, Any], timeout: float) -> httpx.Response:
    with httpx.Client(timeout=timeout) as client:
        return client.post(url, headers=headers, json=body)


def _error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return ""
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("type") or "")[:200]
    return str(error or "")[:200]


def _check(response: httpx.Response, provider: Provider) -> Dict[str, Any]:
    status = response.status_code
    if status in {401, 403}:
        raise OnlineModelError(f"{provider.label} rejected the API key ({provider.key_env}).")
    if status == 429:
        raise OnlineModelError(f"{provider.label} rate limit or credit limit reached.")
    if status >= 400:
        detail = _error_detail(response)
        raise OnlineModelError(f"{provider.label} returned HTTP {status}" + (f": {detail}" if detail else ""))
    try:
        return response.json()
    except ValueError as exc:
        raise OnlineModelError(f"{provider.label} returned an unreadable response.") from exc


def _anthropic(route: OnlineRoute, key: str, system: str, prompt: str, temperature: Optional[float],
               max_tokens: int, timeout: float, post: Poster) -> OnlineResult:
    body: Dict[str, Any] = {"model": route.model, "max_tokens": max_tokens,
                            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    if temperature is not None:
        body["temperature"] = temperature
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    data = _check(post(f"{route.provider.base_url}/messages", headers, body, timeout), route.provider)
    if data.get("stop_reason") == "max_tokens":
        raise OnlineModelError(f"{route.label} stopped at the output limit before finishing.")
    text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    usage = data.get("usage") or {}
    return OnlineResult(text, int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0))


def _openai(route: OnlineRoute, key: str, system: str, prompt: str, temperature: Optional[float],
            max_tokens: int, timeout: float, post: Poster) -> OnlineResult:
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body: Dict[str, Any] = {"model": route.model, "messages": messages}
    # OpenAI's current models take max_completion_tokens; DeepSeek still uses max_tokens.
    body["max_completion_tokens" if route.provider.name == "openai" else "max_tokens"] = max_tokens
    if temperature is not None:
        body["temperature"] = temperature
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    data = _check(post(f"{route.provider.base_url}/chat/completions", headers, body, timeout), route.provider)
    choices = data.get("choices") or []
    if not choices:
        raise OnlineModelError(f"{route.label} returned no answer.")
    if choices[0].get("finish_reason") in {"length", "content_filter"}:
        raise OnlineModelError(f"{route.label} did not finish its answer ({choices[0]['finish_reason']}).")
    text = (choices[0].get("message") or {}).get("content") or ""
    usage = data.get("usage") or {}
    return OnlineResult(text, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0))


def _call(route: OnlineRoute, system: str, prompt: str, temperature: Optional[float], max_tokens: int,
          timeout: float, post: Poster) -> OnlineResult:
    key = _api_key(route.provider)
    if not key:
        raise OnlineModelError(f"No API key for {route.provider.label} ({route.provider.key_env}).")
    send = _anthropic if route.provider.api == "anthropic" else _openai
    try:
        return send(route, key, system, prompt, temperature, max_tokens, timeout, post)
    except OnlineModelError as exc:
        # Some reasoning models accept only their default temperature; ask once more without it.
        if temperature is not None and "temperature" in str(exc).lower():
            return send(route, key, system, prompt, None, max_tokens, timeout, post)
        raise
    except httpx.TimeoutException as exc:
        raise OnlineModelError(f"{route.label} timed out.") from exc
    except httpx.HTTPError as exc:
        raise OnlineModelError(f"{route.provider.label} could not be reached ({type(exc).__name__}).") from exc


def complete(route: OnlineRoute, system: str, prompt: str, *, temperature: Optional[float] = 0.2,
             max_tokens: int = 900, timeout: float = DEFAULT_TIMEOUT_SECONDS, control=None,
             post: Poster = _post) -> OnlineResult:
    """Ask the online model once. A cancelled submission stops waiting at once."""
    max_tokens = max(int(max_tokens), MIN_OUTPUT_TOKENS)
    if control is None:
        result = _call(route, system, prompt, temperature, max_tokens, timeout, post)
    else:
        control.check()
        control.progress("WAITING")
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="online-model")
        try:
            future = pool.submit(_call, route, system, prompt, temperature, max_tokens, timeout, post)
            while not future.done():
                control.check()
                time.sleep(0.1)
            result = future.result()
            control.check()
            control.progress("GENERATING")
        finally:
            # A cancelled request finishes in the background; nothing reads its answer.
            pool.shutdown(wait=False)
    if not result.text.strip():
        raise OnlineModelError(f"{route.label} returned an empty answer.")
    return result


def main() -> int:
    """Show which voters use an online model. `--ping` sends one tiny request per online voter."""
    import sys

    for row in status_report():
        print(f"{row['agent_id']:<11} {row['state']:<28} {row['model'] or row['setting'] or '-'}")
    print(f"Personal context sent online: {'yes' if share_personal_context() else 'no'}; "
          f"token budget per deliberation: {token_budget()}")
    if "--ping" not in sys.argv[1:]:
        return 0
    failed = 0
    for agent_id in TRIBUNAL_AGENT_IDS:
        route = route_for(agent_id)
        if route is None:
            continue
        try:
            result = complete(route, "", "Reply with the single word READY.", temperature=None, max_tokens=16)
            print(f"{agent_id}: {route.label} answered ({result.input_tokens}+{result.output_tokens} tokens)")
        except OnlineModelError as exc:
            failed += 1
            print(f"{agent_id}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
