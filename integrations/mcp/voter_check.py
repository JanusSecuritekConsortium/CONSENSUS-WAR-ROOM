"""Can each tribunal voter's model load and answer on this PC? Run it before a live deliberation, e.g. on new hardware.

    python -m integrations.mcp.voter_check

For RATIONALIS, AETERNUM, BELLATOR and the base model in turn it unloads the other models, asks the configured model
for a few words, and reports whether it loaded, how long the first answer took and how fast it generated. The
model server's own error is shown when a model will not load: a newer llama.cpp can refuse files converted for an
older one. Nothing is saved and no deliberation is started. Refuses while a deliberation is running.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

VOTERS = ("RATIONALIS", "AETERNUM", "BELLATOR")
PROMPT = "Reply with the single word READY."
LOAD_FAILED_HINT = ("the model server could not read this file. A llama.cpp update can drop support for older "
                    "conversions; replace the file with a current one or switch the voter to another model.")


def check_model(base_url: str, model: str, *, timeout: int = 900, post: Optional[Callable] = None,
                clock: Callable[[], float] = time.perf_counter) -> Dict[str, Any]:
    """Load one model by asking it for a few words; the first call includes the time to load the file."""
    if post is None:
        from core.llm import backends
        post = backends.requests.post
    started = clock()
    row: Dict[str, Any] = {"model": model, "ok": False, "seconds": None, "tokens_per_second": None, "error": ""}
    try:
        response = post(f"{base_url.rstrip('/')}/v1/chat/completions", timeout=timeout,
                        json={"model": model, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 8})
        body = response.json() if response.content else {}
    except Exception as error:  # an offline server or a load that outlasts the timeout
        row.update(seconds=round(clock() - started, 1), error=f"{type(error).__name__}: {error}")
        return row
    row["seconds"] = round(clock() - started, 1)
    if not response.ok:
        message = str(((body or {}).get("error") or {}).get("message") or f"HTTP {response.status_code}")
        row["error"] = message + (f"; {LOAD_FAILED_HINT}" if "failed to load" in message else "")
        return row
    speed = ((body or {}).get("timings") or {}).get("predicted_per_second")
    row.update(ok=True, tokens_per_second=round(float(speed), 1) if speed else None)
    return row


def voter_models(config, available: List[str]) -> Dict[str, Optional[str]]:
    """Each voter's configured model as the server names it (None when the server has no such model)."""
    from integrations.msty import api
    wanted = {agent: config.agent_model_overrides.get(agent) for agent in VOTERS}
    wanted["BASE"] = config.base_model
    return {agent: (api.match_model_alias(name, available)[0] if name else None) for agent, name in wanted.items()}


def check(*, config=None, check_one: Callable[[str, str], Dict[str, Any]] = None,
          unload_all: Callable[[str], None] = None, available: Callable[[str], List[str]] = None) -> List[Dict[str, Any]]:
    from integrations.msty import api
    if config is None:
        from config.runtime import load_runtime_config
        from core.paths import CONFIG_PATH
        config = load_runtime_config(CONFIG_PATH)
    base_url = api.resolve_provider_base_url(config)
    check_one = check_one or (lambda url, model: check_model(url, model, timeout=config.generation_timeout_seconds))
    unload_all = unload_all or (lambda url: [api.unload_model(url, name) for name in api.loaded_models(url)])
    available = available or (lambda url: list(api.model_file_sizes(url)))
    rows = []
    for agent, model in voter_models(config, available(base_url)).items():
        if not model:
            rows.append({"agent": agent, "model": None, "ok": False, "seconds": None, "tokens_per_second": None,
                         "error": "the model server does not list this voter's configured model"})
            continue
        unload_all(base_url)  # one voter at a time, as in a deliberation
        rows.append({"agent": agent, **check_one(base_url, model)})
    unload_all(base_url)
    return rows


def render(rows: List[Dict[str, Any]]) -> str:
    lines = []
    for row in rows:
        name = str(row.get("model") or "-").rsplit("/", 1)[-1]
        if row["ok"]:
            speed = f", {row['tokens_per_second']} tokens/s" if row.get("tokens_per_second") else ""
            lines.append(f"{row['agent']:<10} ready     {name}: first answer in {row['seconds']} s{speed}")
        else:
            lines.append(f"{row['agent']:<10} NOT READY {name}: {row['error']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    from integrations.mcp import tribunal_job
    if tribunal_job.deliberation_running():
        print("A deliberation is running; check the voters after it finishes.")
        return 2
    tribunal_job._free_local_ai()
    rows = check()
    print(render(rows))
    return 0 if all(row["ok"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
