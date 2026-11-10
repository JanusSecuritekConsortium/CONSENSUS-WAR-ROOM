"""Tribunal deliberations requested over the CONSENSUS MCP connection, run in their own process.

    python -m integrations.mcp.tribunal_job TICKET   # run the deliberation saved under TICKET

A deliberation takes minutes on local models, longer than an MCP call waits, so `start` saves the question as a
job record, launches this module detached and returns a ticket; `status` reads the record. One deliberation runs
at a time because the voters share one GPU. Records live in the git-ignored _ARBITER/memory folder.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import uuid
from typing import Any, Callable, Dict, Optional

from core.paths import ARBITER_DIR

JOBS_DIR = ARBITER_DIR / "memory" / "tribunal_jobs"
MAX_QUERY_CHARS = 4000
STALE_AFTER = timedelta(hours=2)  # a job with no heartbeat this long after it was requested never ran
HEARTBEAT_EVERY = 60  # seconds; a running deliberation touches <ticket>.alive this often
HEARTBEAT_STALE = timedelta(minutes=5)  # a heartbeat older than this means the run died without saying so


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _path(ticket: str, jobs_dir: Path) -> Path:
    if not ticket or not all(char in "0123456789abcdef" for char in ticket):
        raise ValueError("Unknown ticket")
    return jobs_dir / f"{ticket}.json"


def _write(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stale(record: Dict[str, Any], path: Path) -> bool:
    """An unfinished job whose process is gone: its heartbeat stopped, or it never started one."""
    alive = path.with_suffix(".alive")
    try:
        beat = datetime.fromtimestamp(alive.stat().st_mtime, timezone.utc)
    except OSError:
        return _now() - datetime.fromisoformat(record["requested_at"]) >= STALE_AFTER
    return _now() - beat >= HEARTBEAT_STALE


def _running(jobs_dir: Path) -> Optional[Dict[str, Any]]:
    for path in jobs_dir.glob("*.json") if jobs_dir.exists() else ():
        try:
            record = _read(path)
        except (OSError, ValueError):
            continue
        if record.get("status") in ("queued", "running") and not _stale(record, path):
            return record
    return None


def deliberation_running(jobs_dir: Path = JOBS_DIR) -> bool:
    """True while a tribunal deliberation holds the GPU; other local model work should wait for it."""
    return _running(jobs_dir) is not None


def _free_local_ai() -> list:
    """Unload Msty's Local AI models (an Ollama-compatible server), which would otherwise hold the GPU and RAM."""
    from config.runtime import load_runtime_config
    from core.paths import CONFIG_PATH
    from integrations.msty import api
    return api.unload_ollama_models(load_runtime_config(CONFIG_PATH).msty_base_url)


def _launch(ticket: str) -> None:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([sys.executable, "-m", "integrations.mcp.tribunal_job", ticket],
                     cwd=str(Path(__file__).resolve().parents[2]), stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)


def _free_gpu_bytes() -> int:
    try:
        completed = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=10,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return sum(int(line) for line in completed.stdout.split() if line.strip().isdigit()) * 2**20
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def _guest_local_only() -> bool:
    from core.llm import online
    return online.setting("CONSENSUS_GUEST_ONLINE", "0") != "1"


def memory_note(*, local_only: bool = False) -> Optional[str]:
    """A warning when the largest voter model will not fit in the free RAM and graphics memory; None if it fits.

    A model larger than what is free makes the model server refuse it, or pushes the whole PC out of memory.
    """
    try:
        import psutil
        from config.runtime import load_runtime_config
        from core.paths import CONFIG_PATH
        from integrations.msty import api
        config = load_runtime_config(CONFIG_PATH)
        base_url = api.resolve_provider_base_url(config)
        sizes = api.model_file_sizes(base_url)
        from core.llm import online
        # Voters on an online model load nothing locally unless every online attempt fails.
        voters = {agent: api.match_model_alias(name, list(sizes))[0] for agent, name in config.agent_model_overrides.items()
                  if local_only or not online.routes_for(agent)}
        needed = {agent: sizes[model] for agent, model in voters.items() if model}
        if not needed:
            return None
        resident = sum(sizes.get(model, 0) for model in api.loaded_models(base_url) if model in voters.values())
        free = psutil.virtual_memory().available + _free_gpu_bytes() + resident
    except Exception:
        return None
    agent = max(needed, key=needed.get)
    if needed[agent] <= free:
        return None
    gb = lambda value: f"{value / 2**30:.0f} GB"
    return (f"Low memory: {agent}'s model needs about {gb(needed[agent])}, but only about {gb(free)} of RAM and "
            "graphics memory is free. The deliberation will probably fail or slow the PC; close other programs "
            "or unload other models first.")


def start(query: str, *, jobs_dir: Path = JOBS_DIR, launch: Callable[[str], None] = _launch,
          check_memory: Optional[Callable[[], Optional[str]]] = None,
          free_local_ai: Callable[[], list] = lambda: _free_local_ai(), guest: bool = False,
          guest_limit: Optional[int] = None) -> Dict[str, Any]:
    """Queue a deliberation and return a ticket.

    guest=True is a question from another system (integrations.guest): it never unloads the owner's
    Local AI models, never learns about the owner's own deliberations, and runs as a guest deliberation.
    """
    query = " ".join(str(query or "").split())
    if not query:
        raise ValueError("A question is required")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"Questions are limited to {MAX_QUERY_CHARS} characters")
    from core.history import unfilled_template_fields
    blanks = unfilled_template_fields(query)
    if len(blanks) >= 2:
        raise ValueError("The question is an unfilled template; fill in " + ", ".join(blanks) + " first")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    # Both entry points reserve jobs under the same cross-process SQLite writer lock.
    # SQLite releases the lock if the admitting process exits unexpectedly.
    with closing(sqlite3.connect(jobs_dir / "admission.sqlite3", timeout=0)) as gate:
        try:
            gate.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as error:
            if str(error) != "database is locked":
                raise
            return {"status": "busy", "detail": "The tribunal is admitting another request; try again later."}
        with gate:
            return _admit(query, jobs_dir, launch, check_memory, free_local_ai, guest, guest_limit)


def _admit(query, jobs_dir, launch, check_memory, free_local_ai, guest, guest_limit):
    if guest and guest_limit is not None and guest_daily_count(jobs_dir) >= guest_limit:
        return {"status": "limit_reached", "detail": "The daily limit of guest questions is reached."}
    busy = _running(jobs_dir)
    if busy:
        if guest:
            return {"status": "busy", "detail": "The tribunal is busy with another deliberation; try again later."}
        return {"status": "busy", "ticket": busy["ticket"],
                "detail": "Another deliberation is running; ask again when tribunal_verdict reports it finished."}
    if not guest:
        try:  # before measuring: Local AI's assistant model is memory the tribunal can reclaim
            free_local_ai()
        except Exception:
            pass
    local_only = guest and _guest_local_only()
    warning = check_memory() if check_memory is not None else memory_note(local_only=local_only)
    if warning:
        return {"status": "not_started", "detail": warning}
    ticket = uuid.uuid4().hex[:12]
    record = {"ticket": ticket, "query": query, "status": "queued", "requested_at": _now().isoformat(timespec="seconds")}
    if guest:
        record.update(guest=True, guest_local_only=local_only)
    path = _path(ticket, jobs_dir)
    _write(path, record)
    try:
        launch(ticket)
    except Exception:
        detail = "The tribunal worker could not start."
        record.update(status="failed", error=detail, launch_failed=True, finished_at=_now().isoformat())
        _write(path, record)
        return {"status": "not_started", "detail": detail}
    return {"status": "queued", "ticket": ticket,
            "detail": "The tribunal is deliberating; on local models this can take an hour. Check with tribunal_verdict."}


def summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """The verdict as a caller needs it: no raw model output or transcripts."""
    return {
        "session_id": result.get("session_id"),
        "verdict": result.get("verdict"),
        "confidence": result.get("confidence"),
        "reason": result.get("reason"),
        "votes": {agent: {"vote": (vote or {}).get("vote"), "confidence": (vote or {}).get("confidence"),
                          "reasoning": str((vote or {}).get("reasoning") or "")[:600]}
                  for agent, vote in (result.get("votes") or {}).items()},
        "next_steps": list(result.get("next_steps") or [])[:5],
        "review_triggers": list(result.get("review_triggers") or [])[:10],
    }


def status(ticket: str, *, jobs_dir: Path = JOBS_DIR) -> Dict[str, Any]:
    path = _path(ticket, jobs_dir)
    if not path.exists():
        raise ValueError("Unknown ticket")
    record = _read(path)
    if record.get("status") in ("queued", "running") and _stale(record, path):
        record.update(status="failed", error="The deliberation stopped without reporting a result.")
    elif record.get("status") == "running" and record.get("started_at"):
        record["elapsed_minutes"] = int((_now() - datetime.fromisoformat(record["started_at"])).total_seconds() // 60)
    return record


def run(ticket: str, *, jobs_dir: Path = JOBS_DIR, deliberate: Optional[Callable[[str], Any]] = None) -> Dict[str, Any]:
    path = _path(ticket, jobs_dir)
    record = _read(path)
    if record.get("status") != "queued":
        return record
    record.update(status="running", started_at=_now().isoformat(timespec="seconds"))
    _write(path, record)
    alive, done = path.with_suffix(".alive"), threading.Event()

    def beat() -> None:
        while True:
            alive.touch()
            if done.wait(HEARTBEAT_EVERY):
                return
    heartbeat = threading.Thread(target=beat, daemon=True)
    heartbeat.start()
    try:
        guest = bool(record.get("guest"))
        if deliberate is None and not guest:
            try:  # a 9B assistant model on the GPU pushes the 18 GB voter models into the page file
                record["freed_models"] = _free_local_ai()
            except Exception:
                pass
        from core.history import result_to_dict
        result = deliberate(record["query"]) if deliberate else _deliberate(
            record["query"], guest=guest, guest_local_only=record.get("guest_local_only"))
        record.update(status="finished", result=summary(result_to_dict(result)))
    except Exception as error:  # the record is the only place a windowless run can report
        record.update(status="failed", error=str(error)[:500])
    finally:
        done.set()
        heartbeat.join()
        alive.unlink(missing_ok=True)
    record["finished_at"] = _now().isoformat(timespec="seconds")
    _write(path, record)
    return record


def guest_daily_count(jobs_dir: Path = JOBS_DIR, *, now: Optional[datetime] = None) -> int:
    """Guest deliberations requested in the last 24 hours."""
    since = (now or _now()) - timedelta(hours=24)
    count = 0
    for path in jobs_dir.glob("*.json") if jobs_dir.exists() else ():
        try:
            record = _read(path)
            if (record.get("guest") and not record.get("launch_failed")
                    and datetime.fromisoformat(record["requested_at"]) >= since):
                count += 1
        except (OSError, ValueError, KeyError):
            continue
    return count


def _deliberate(query: str, guest: bool = False, *, guest_local_only: Optional[bool] = None):
    """The same tribunal the command line builds from the runtime config.

    A guest deliberation uses local models only unless CONSENSUS_GUEST_ONLINE=1, so another system's
    questions never go out on the owner's Claude, ChatGPT or Grok subscriptions.
    """
    import os
    if guest and (guest_local_only is True or _guest_local_only()):
        os.environ["CONSENSUS_ONLINE_MODELS"] = "0"  # this process runs only this one deliberation
    from config.nodes import DEFAULT_NODES, apply_node_overrides
    from config.runtime import load_runtime_config
    from core.paths import CONFIG_PATH
    from core.tribunal import Tribunal
    from core.voting.rules import ConsensusRules
    from integrations.msty.runtime import MstyRuntime
    config = load_runtime_config(CONFIG_PATH)
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    rules = ConsensusRules(
        minimum_confidence=config.minimum_confidence, quorum=config.quorum, majority=config.majority,
        high_risk_review=config.high_risk_review, evidence_threshold=config.evidence_threshold,
        classification_confidence_threshold=config.classification_confidence_threshold,
        tie_break_priority=config.tie_break_priority, proposal_taxonomy=config.proposal_taxonomy,
        monolith_domain_map=config.monolith_domain_map,
    )
    return Tribunal(nodes, MstyRuntime(config), rules=rules, theme_key=config.theme).deliberate(
        query, sequential=config.sequential, guest=guest)


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m integrations.mcp.tribunal_job TICKET")
        return 2
    return 0 if run(args[0]).get("status") == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
