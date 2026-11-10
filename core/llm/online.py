"""Online models for tribunal voters: Anthropic (Claude), OpenAI (GPT/Codex) and DeepSeek.

A voter goes online only when the operator names a model for it, for example in the
gitignored `.env` file beside the code:

    CONSENSUS_ONLINE_MODEL_RATIONALIS=claude-cli:sonnet      # Claude subscription via Claude Code
    CONSENSUS_ONLINE_MODEL_AETERNUM=codex-cli:default        # ChatGPT subscription via Codex CLI
    CONSENSUS_ONLINE_MODEL_BELLATOR=deepseek:deepseek-chat   # paid API
    DEEPSEEK_API_KEY=...

API providers need their key; subscription providers (`*-cli`) need their command-line tool
installed and signed in. Otherwise the voter stays on its local model. A failed online call is
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
    api: str  # "anthropic", "openai" or "cli"
    command: str = ""  # the command-line tool for subscription providers
    # API keys removed from the tool's environment, so it signs in with the subscription instead.
    strip_env: tuple = ()

    @property
    def subscription(self) -> bool:
        return self.api == "cli"


PROVIDERS: Dict[str, Provider] = {
    "anthropic": Provider("anthropic", "Claude (Anthropic)", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "anthropic"),
    "openai": Provider("openai", "OpenAI (GPT / Codex)", "https://api.openai.com/v1", "OPENAI_API_KEY", "openai"),
    "deepseek": Provider("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "openai"),
    "xai": Provider("xai", "Grok (xAI)", "https://api.x.ai/v1", "XAI_API_KEY", "openai"),
    "claude-cli": Provider("claude-cli", "Claude subscription (Claude Code)", "", "", "cli", "claude",
                           ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDECODE")),
    "codex-cli": Provider("codex-cli", "ChatGPT subscription (Codex CLI)", "", "", "cli", "codex",
                          ("OPENAI_API_KEY", "CODEX_API_KEY")),
    "grok-cli": Provider("grok-cli", "Grok subscription (Grok CLI)", "", "", "cli", "grok", ("XAI_API_KEY",)),
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


def _file_values(*, fresh: bool = False) -> Dict[str, str]:
    path = _env_file()
    if path is None or not path.is_file():
        return {}
    mtime = path.stat().st_mtime
    if fresh or _env_file_cache["path"] != path or _env_file_cache["mtime"] != mtime:
        try:
            from dotenv import dotenv_values
            values = {key: value for key, value in dotenv_values(path).items() if value is not None}
        except Exception:
            values = {}
        if fresh:
            return values
        _env_file_cache.update(path=path, mtime=mtime, values=values)
    return _env_file_cache["values"]


def setting(name: str, default: str = "", *, fresh: bool = False) -> str:
    """The process environment wins over the .env file, so one run can override a stored choice."""
    value = os.environ.get(name)
    if value is None:
        value = _file_values(fresh=fresh).get(name)
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
    return setting(provider.key_env) if provider.key_env else ""


_which_cache: Dict[str, tuple[float, Optional[str]]] = {}


def _cli_path(provider: Provider) -> Optional[str]:
    """The tool's path; looked up at most once a minute, because the GUI asks on every refresh."""
    import shutil

    if not provider.command:
        return None
    now = time.monotonic()
    cached = _which_cache.get(provider.command)
    if cached is None or now - cached[0] > 60:
        cached = (now, shutil.which(provider.command))
        _which_cache[provider.command] = cached
    return cached[1]


SHORT_NAMES = {"anthropic": "Claude", "openai": "OpenAI", "deepseek": "DeepSeek", "xai": "Grok",
               "claude-cli": "Claude", "codex-cli": "ChatGPT", "grok-cli": "Grok"}


def display_name(route: OnlineRoute) -> str:
    """A short card label, e.g. "Claude sonnet · subscription" or "DeepSeek deepseek-chat · API"."""
    model = "" if route.model.lower() == "default" else f" {route.model}"
    kind = "subscription" if route.provider.subscription else "API"
    return f"{SHORT_NAMES.get(route.provider.name, route.provider.name)}{model} · {kind}"


def _usable(provider: Provider) -> bool:
    return bool(_cli_path(provider)) if provider.subscription else bool(_api_key(provider))


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
    if route is None or not _usable(route.provider):
        return None
    return route


def backup_route(agent_id: str) -> Optional[OnlineRoute]:
    """The shared backup model (CONSENSUS_ONLINE_FALLBACK), or None when unset or unusable."""
    value = setting("CONSENSUS_ONLINE_FALLBACK")
    route = parse_route(agent_id.upper(), value) if value and online_enabled() else None
    return route if route is not None and _usable(route.provider) else None


def routes_for(agent_id: str) -> list[OnlineRoute]:
    """The online models a voter tries in order: its own, then the shared backup.

    Only voters given an online model use the backup; the others stay local.
    """
    if configured_route(agent_id) is None:
        return []
    routes = [route for route in (route_for(agent_id), backup_route(agent_id)) if route is not None]
    return [route for index, route in enumerate(routes) if route.label not in {r.label for r in routes[:index]}]


def setting_state(agent_id: str, raw: str) -> tuple[Optional[bool], str]:
    """(ready, plain words) for one stored setting: True ready, False needs attention, None stays local."""
    if not raw:
        return None, "local"
    if not online_enabled():
        return None, "disabled"
    route = parse_route(agent_id, raw)
    if route is None:
        return False, "invalid setting"
    if route.provider.subscription and not _cli_path(route.provider):
        return False, f"'{route.provider.command}' not installed"
    if not route.provider.subscription and not _api_key(route.provider):
        return False, f"no key ({route.provider.key_env})"
    return True, "online" if agent_id in TRIBUNAL_AGENT_IDS else "ready"


def status_report() -> list[Dict[str, Any]]:
    """Per voter: the configured online model and whether its key is present. Never the key itself."""
    rows = []
    for agent_id in TRIBUNAL_AGENT_IDS:
        raw = setting(ENV_PREFIX + agent_id)
        route = configured_route(agent_id)
        rows.append({"agent_id": agent_id, "setting": raw, "model": route.label if route else "",
                     "state": setting_state(agent_id, raw)[1]})
    return rows


# ---- the Online voters screen ------------------------------------------------------------------

BACKUP_ENV = "CONSENSUS_ONLINE_FALLBACK"
# The choices offered on the Online voters screen; any other stored value is kept and shown as is.
CHOICES: list[tuple[str, str]] = [
    ("", "Local model (Msty)"),
    ("claude-cli:sonnet", "Claude Sonnet - subscription"),
    ("claude-cli:opus", "Claude Opus - subscription"),
    ("codex-cli:default", "ChatGPT - subscription"),
    ("grok-cli:default", "Grok - subscription"),
    ("deepseek:deepseek-chat", "DeepSeek chat - paid API"),
    ("deepseek:deepseek-reasoner", "DeepSeek reasoner - paid API"),
    ("anthropic:claude-sonnet-5-5", "Claude Sonnet - paid API"),
]


def choice_label(value: str) -> str:
    return next((label for key, label in CHOICES if key == value), value)


def voter_overview() -> list[Dict[str, Any]]:
    """One row per voter plus the shared backup, for the Online voters screen. Never contains a key."""
    rows = []
    for agent_id, env in [*((a, ENV_PREFIX + a) for a in TRIBUNAL_AGENT_IDS), ("BACKUP", BACKUP_ENV)]:
        raw = setting(env)
        ready, state = setting_state(agent_id, raw)
        rows.append({"key": agent_id, "env": env, "value": raw, "label": choice_label(raw), "ready": ready,
                     "state": state, "overridden": os.environ.get(env) is not None})
    return rows


def _env_line_key(line: str) -> str:
    text = line.strip()
    if not text or text.startswith("#") or "=" not in text:
        return ""
    name = text.split("=", 1)[0].strip()
    return name[len("export "):].strip() if name.startswith("export ") else name


def save_settings(updates: Dict[str, str], *, prefix: str = "CONSENSUS_ONLINE_") -> Path:
    """Write CONSENSUS settings into the .env file, keeping every other line as it is.

    Only names starting with `prefix` (online-voter settings by default; the guest door passes
    CONSENSUS_GUEST_) are accepted, so this can never write or move a provider API key.
    """
    if not prefix.startswith("CONSENSUS_"):
        raise ValueError("Only CONSENSUS settings can be saved here.")
    for name, value in updates.items():
        if not name.startswith(prefix) or any(c in str(value) for c in "\r\n"):
            raise ValueError(f"Not a {prefix}* setting: {name}")
    path = _env_file()
    if path is None:
        raise ValueError("No settings file is configured (CONSENSUS_ONLINE_ENV_FILE is empty).")
    original = path.read_bytes().decode("utf-8") if path.is_file() else ""
    lines = original.splitlines()
    newline = "\r\n" if "\r\n" in original else "\n"
    pending = dict(updates)
    for index, line in enumerate(lines):
        name = _env_line_key(line)
        if name in pending:
            lines[index] = f"{name}={pending.pop(name)}"
    lines.extend(f"{name}={value}" for name, value in pending.items())
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes((newline.join(lines) + newline).encode("utf-8"))  # keeps the file's line endings
    temporary.replace(path)
    _env_file_cache.update(path=None, mtime=None, values={})
    return path


def test_setting(agent_id: str, raw: str, timeout: float = 120.0) -> tuple[bool, str]:
    """Send one tiny question to the model a setting names; (worked, plain words)."""
    ready, state = setting_state(agent_id, raw)
    if not ready:
        return False, "Nothing to test: local model." if ready is None else f"Not ready: {state}."
    route = parse_route(agent_id if agent_id in TRIBUNAL_AGENT_IDS else TRIBUNAL_AGENT_IDS[0], raw)
    started = time.monotonic()
    try:
        complete(route, "", "Reply with the single word READY.", temperature=None, max_tokens=16, timeout=timeout)
    except OnlineModelError as exc:
        return False, str(exc)[:300]
    return True, f"Answered in {time.monotonic() - started:.0f} s."


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


CLI_TIMEOUT_SECONDS = 900.0


def _cli_workdir() -> Path:
    """An empty folder: the tools run here so they never see or touch CONSENSUS files."""
    from core.paths import SYSTEM_ROOT

    folder = SYSTEM_ROOT / ".local" / "voter-cli"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def cli_command(route: OnlineRoute, system_text: str, prompt_file: Path, system_file: Path,
                output_file: Path) -> list[str]:
    """The tool's single-answer mode with its tools, web search and plugins switched off."""
    exe = _cli_path(route.provider) or route.provider.command
    model = [] if route.model.lower() == "default" else ["--model", route.model]
    name = route.provider.name
    if name == "claude-cli":
        return [exe, "-p", "--output-format", "json", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
                "--no-session-persistence", "--system-prompt-file", str(system_file), *model]
    if name == "codex-cli":
        return [exe, "exec", "--skip-git-repo-check", "--sandbox", "read-only", "--ephemeral", "--ignore-user-config",
                "--ignore-rules", "--color", "never", "--json", "-o", str(output_file), *model, "-"]
    return [exe, "--prompt-file", str(prompt_file), "--system-prompt-override", system_text,
            "--output-format", "plain", "--disable-web-search", "--no-subagents", "--max-turns", "1",
            "--permission-mode", "dontAsk", *model]


def _cli_env(provider: Provider) -> Dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in provider.strip_env}
    env["NO_COLOR"] = "1"
    return env


def _cli_result(route: OnlineRoute, stdout: str, output_file: Path) -> OnlineResult:
    import json

    if route.provider.name == "claude-cli":
        try:
            data = json.loads(stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise OnlineModelError(f"{route.label} returned an unreadable answer.") from exc
        if data.get("is_error"):
            raise OnlineModelError(f"{route.label} failed: {str(data.get('result') or data.get('subtype'))[:200]}")
        usage = data.get("usage") or {}
        tokens_in = sum(int(usage.get(key) or 0) for key in
                        ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        return OnlineResult(str(data.get("result") or ""), tokens_in, int(usage.get("output_tokens") or 0))
    if route.provider.name == "codex-cli":
        text = output_file.read_text(encoding="utf-8") if output_file.is_file() else ""
        for line in reversed(stdout.splitlines()):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("type") != "turn.completed":
                continue
            usage = event.get("usage")
            if isinstance(usage, dict):
                input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
                if type(input_tokens) is int and type(output_tokens) is int and min(input_tokens, output_tokens) >= 0:
                    return OnlineResult(text, input_tokens, output_tokens)
            break
        return OnlineResult(text, 0, 0)
    return OnlineResult(stdout, 0, 0)


def _wait(process, stdin_text: str, timeout: float, control) -> tuple[str, str]:
    """Wait for the tool while honouring cancellation and the time limit."""
    import threading

    result: Dict[str, Any] = {}
    worker = threading.Thread(target=lambda: result.update(out=process.communicate(stdin_text)), daemon=True)
    worker.start()
    started = time.monotonic()
    while worker.is_alive():
        if control is not None:
            try:
                control.check()
            except BaseException:
                process.kill()
                raise
        if time.monotonic() - started > timeout:
            process.kill()
            worker.join(5)
            raise OnlineModelError("The subscription tool timed out.")
        worker.join(0.2)
    return result.get("out", ("", ""))


def _call_cli(route: OnlineRoute, system: str, prompt: str, timeout: float, control=None) -> OnlineResult:
    """Run the subscription tool once. The prompt goes through stdin or a file, never the command line."""
    import subprocess
    import tempfile

    if not _cli_path(route.provider):
        raise OnlineModelError(f"'{route.provider.command}' is not installed for {route.provider.label}.")
    system_text = system or "You are a tribunal voter. Answer in the requested format."
    # Codex has no separate system prompt; the instructions lead the prompt instead.
    stdin_text = f"{system_text}\n\n{prompt}" if route.provider.name == "codex-cli" else prompt
    with tempfile.TemporaryDirectory(prefix="consensus-voter-") as scratch:
        folder = Path(scratch)
        system_file, prompt_file, output_file = folder / "system.txt", folder / "prompt.txt", folder / "answer.txt"
        system_file.write_text(system_text, encoding="utf-8")
        prompt_file.write_text(prompt, encoding="utf-8")
        process = subprocess.Popen(
            cli_command(route, system_text, prompt_file, system_file, output_file),
            cwd=_cli_workdir(), env=_cli_env(route.provider), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            stdout, stderr = _wait(process, stdin_text, timeout, control)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        if process.returncode != 0:
            lines = (stderr or stdout or "").strip().splitlines()
            message = lines[-1][:200] if lines else f"exit code {process.returncode}"
            if any(word in message.lower() for word in ("sign", "login", "auth")):
                message = f"not signed in ({message})"
            raise OnlineModelError(f"{route.provider.label} failed: {message}")
        return _cli_result(route, stdout, output_file)


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
    if route.provider.subscription:
        if control is not None:
            control.check()
            control.progress("WAITING")
        result = _call_cli(route, system, prompt, max(timeout, CLI_TIMEOUT_SECONDS), control)
        if control is not None:
            control.check()
            control.progress("GENERATING")
    elif control is None:
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
    backup = setting(BACKUP_ENV)
    if backup:
        print(f"{'BACKUP':<11} {setting_state('BACKUP', backup)[1]:<28} {backup}")
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
