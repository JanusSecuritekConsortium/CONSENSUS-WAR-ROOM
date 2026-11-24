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
ANSWER_WAIT = timedelta(hours=24)  # how long a vote waits for the owner's answers before it ends with its result
ANSWER_POLL = 15  # seconds between looks at the record while waiting for answers
MAX_ANSWER_CHARS = 4000
# A job in any of these states holds the tribunal: no second deliberation starts.
ACTIVE = ("queued", "running", "awaiting_answers", "answered", "declined")
WAITING = ("awaiting_answers", "answered", "declined")  # paused for the owner: the models are idle


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


def _worker_alive(record: Dict[str, Any]) -> bool:
    """The worker process named in the record still exists (same process, not a reused number)."""
    pid, born = record.get("worker_pid"), record.get("worker_started")
    if not isinstance(pid, int) or not isinstance(born, (int, float)):
        return False
    try:
        import psutil
        process = psutil.Process(pid)
        return process.is_running() and abs(process.create_time() - born) < 2
    except Exception:
        return False


def _stale(record: Dict[str, Any], path: Path) -> bool:
    """An unfinished job whose process is gone: its heartbeat stopped, or it never started one.

    Loading an 18 GB voter model can freeze the worker (and its heartbeat) for several minutes
    when memory is tight (test vote 6, 17 Nov 2026), so a live worker process counts as running.
    """
    if _worker_alive(record):
        return False
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
        if record.get("status") in ACTIVE and not _stale(record, path):
            return record
    return None


def deliberation_running(jobs_dir: Path = JOBS_DIR) -> bool:
    """True while a tribunal deliberation holds the GPU; other local model work should wait for it.
    A vote paused for the owner's answers leaves the GPU free."""
    record = _running(jobs_dir)
    return record is not None and record.get("status") not in WAITING


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
    from integrations.msty import api
    return api.free_gpu_bytes()


def _guest_local_only() -> bool:
    from core.llm import online
    return online.setting("CONSENSUS_GUEST_ONLINE", "0") != "1"


def memory_note(*, local_only: bool = False) -> Optional[str]:
    """A warning when the largest voter model will not fit in the free RAM and graphics memory; None if it fits.

    A model larger than what is free makes the model server refuse it, or pushes the whole PC into swap, where
    one answer takes twenty minutes instead of two (test vote 8). The model also needs MEMORY_HEADROOM_BYTES.
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
        from config.names import TRIBUNAL_AGENT_IDS
        from config.nodes import DEFAULT_NODES, apply_node_overrides
        overrides = dict(config.agent_model_overrides or {})
        node_overrides = config.node_overrides if isinstance(getattr(config, "node_overrides", None), dict) else {}
        nodes = apply_node_overrides(DEFAULT_NODES, node_overrides)
        # A voter without its own model setting uses its node's model, so it is measured too (DeepSeek, 2026-11-24).
        names = {agent: overrides.get(agent) or getattr(nodes.get(agent), "model", "") for agent in TRIBUNAL_AGENT_IDS}
        names.update({agent: name for agent, name in overrides.items() if agent not in names})
        # Voters on an online model load nothing locally unless every online attempt fails.
        needed = {}
        for agent, name in names.items():
            if not name or not (local_only or not online.routes_for(agent)):
                continue
            # The runtime moves on to a smaller same-maker backup when the main model does not fit
            # (9.21.1), so a voter fits when its smallest allowed model fits (Codex review 2026-11-24).
            usable = [sizes[model] for model in api.real_model_candidates(agent, name, list(sizes), config)
                      if model in sizes]
            if usable:
                needed[agent] = min(usable)
        if not needed:
            return None
        # Every model the router holds is unloaded before a voter's model loads, so its memory counts as free.
        resident = sum(sizes.get(model, 0) for model in api.loaded_models(base_url))
        free = psutil.virtual_memory().available + _free_gpu_bytes() + resident
    except Exception:
        return None
    agent = max(needed, key=needed.get)
    if needed[agent] + api.MEMORY_HEADROOM_BYTES <= free:
        return None
    gb = lambda value: f"{value / 2**30:.0f} GB"
    return (f"Low memory: {agent}'s model needs about {gb(needed[agent])} (its smallest allowed model, backups "
            f"included), but only about {gb(free)} of RAM and "
            "graphics memory is free. The deliberation will probably fail or slow the PC; close other programs "
            "or unload other models first.")


def start(query: str, *, jobs_dir: Path = JOBS_DIR, launch: Callable[[str], None] = _launch,
          check_memory: Optional[Callable[[], Optional[str]]] = None,
          free_local_ai: Callable[[], list] = lambda: _free_local_ai(), guest: bool = False,
          guest_limit: Optional[int] = None, submitted_by: Optional[str] = None,
          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Queue a deliberation and return a ticket.

    options carries a web API caller's choices for this vote: theme, sequential, minimum_confidence, source.

    submitted_by names the signed-in operator (the phone page passes it); the worker
    records it on the decision.

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
            return _admit(query, jobs_dir, launch, check_memory, free_local_ai, guest, guest_limit, submitted_by,
                          options)


def _admit(query, jobs_dir, launch, check_memory, free_local_ai, guest, guest_limit, submitted_by=None, options=None):
    if guest and guest_limit is not None and guest_daily_count(jobs_dir) >= guest_limit:
        return {"status": "limit_reached", "detail": "The daily limit of guest questions is reached."}
    busy = _running(jobs_dir)
    if busy:
        if guest:
            return {"status": "busy", "detail": "The tribunal is busy with another deliberation; try again later."}
        if busy.get("status") == "awaiting_answers":
            return {"status": "busy", "ticket": busy["ticket"], "questions": busy.get("questions", []),
                    "detail": "The tribunal is waiting for the owner's answers to its voters' questions on this ticket; "
                              "answer them (or stop the questions) with tribunal_answer first."}
        return {"status": "busy", "ticket": busy["ticket"],
                "detail": "Another deliberation is running; ask again when tribunal_verdict reports it finished."}
    from core import vote_lock
    held = vote_lock.holder()
    if held:  # a vote from the desktop window or the command line holds the voters' graphics card
        return {"status": "busy", "detail": held["detail"]}
    if not guest:
        try:  # before measuring: Local AI's assistant model is memory the tribunal can reclaim
            free_local_ai()
        except Exception:
            pass  # best effort; the worker tries again and records a failure on the ticket
    local_only = guest and _guest_local_only()
    warning = check_memory() if check_memory is not None else memory_note(local_only=local_only)
    if warning:
        return {"status": "not_started", "detail": warning}
    ticket = uuid.uuid4().hex[:12]
    record = {"ticket": ticket, "query": query, "status": "queued", "requested_at": _now().isoformat(timespec="seconds")}
    if options:
        record["options"] = {key: options[key] for key in ("theme", "sequential", "minimum_confidence", "source")
                             if options.get(key) is not None}
    if guest:
        record.update(guest=True, guest_local_only=local_only)
    elif submitted_by:
        record["submitted_by"] = str(submitted_by)[:64]
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
    if record.get("status") in ACTIVE and _stale(record, path):
        record.update(status="failed", error="The deliberation stopped without reporting a result.")
    elif record.get("status") in ("running", *WAITING) and record.get("started_at"):
        record["elapsed_minutes"] = int((_now() - datetime.fromisoformat(record["started_at"])).total_seconds() // 60)
        if record.get("status") == "running" and _progress_detail(record):
            record["detail"] = _progress_detail(record)
    if record.get("status") == "awaiting_answers":
        record["detail"] = ("The voters could not agree and are waiting for the owner's answers to their questions. "
                            "Answer with tribunal_answer; the vote then reruns with the answers. Without an answer "
                            f"it ends with its current result after {int(ANSWER_WAIT.total_seconds() // 3600)} hours.")
    return record


def answer(ticket: str, text: str = "", *, stop: bool = False, jobs_dir: Path = JOBS_DIR) -> Dict[str, Any]:
    """Give the owner's answer to the voters' questions on a paused vote, or stop asking (the vote then
    ends with its current result). Only a vote waiting for answers accepts one."""
    path = _path(ticket, jobs_dir)
    if not path.exists():
        raise ValueError("Unknown ticket")
    record = status(ticket, jobs_dir=jobs_dir)
    if record.get("status") != "awaiting_answers":
        raise ValueError("This ticket is not waiting for answers")
    text = " ".join(str(text or "").split())
    if not stop and not text:
        raise ValueError("An answer is required (or stop the questions)")
    if len(text) > MAX_ANSWER_CHARS:
        raise ValueError(f"Answers are limited to {MAX_ANSWER_CHARS} characters")
    stored = _read(path)
    stored.update(status="declined" if stop else "answered", answer="" if stop else text,
                  answer_given_at=_now().isoformat(timespec="seconds"))
    _write(path, stored)
    return {"ticket": ticket, "status": stored["status"],
            "detail": "The vote ends with its current result." if stop else "Answer received; the vote reruns with it."}


def _asker(path: Path, record: Dict[str, Any], *, wait: timedelta = ANSWER_WAIT, poll: float = ANSWER_POLL,
           sleep: Callable[[float], None] = None) -> Callable[[list], Optional[str]]:
    """ask_owner for a job: pause the record with the voters' questions and wait for answer()."""
    import time
    pause = sleep or time.sleep

    def ask(questions: list) -> Optional[str]:
        record.update(status="awaiting_answers", questions=questions, asked_at=_now().isoformat(timespec="seconds"))
        record.pop("answer", None)
        _write(path, record)
        from core.notify import questions_alert
        questions_alert(questions)  # a Windows notification, so the owner knows the vote is waiting
        deadline = _now() + wait
        reply: Optional[str] = None
        outcome = "unanswered"
        while _now() < deadline:
            pause(poll)
            try:
                current = _read(path)
            except (OSError, ValueError):
                continue
            if current.get("status") == "answered":
                reply, outcome = str(current.get("answer") or ""), "answered"
                break
            if current.get("status") == "declined":
                outcome = "stopped"
                break
        record.setdefault("owner_rounds", []).append({
            "questions": questions, "asked_at": record.get("asked_at"), "outcome": outcome,
            "answer": reply or "", "answered_at": _now().isoformat(timespec="seconds")})
        for key in ("questions", "asked_at", "answer", "answer_given_at"):
            record.pop(key, None)
        record["status"] = "running"
        _write(path, record)
        return reply
    return ask


def _progress(path: Path, record: Dict[str, Any]) -> Callable[[Dict[str, Any]], None]:
    """on_event for a job: keep the round, voter and model on the ticket, so a status check can tell a
    slow model load from a later round or a backup attempt (Codex review 2026-11-24)."""
    def note(event: Dict[str, Any]) -> None:
        kind = event.get("type")
        if kind not in ("round_started", "agent_started", "vote_received", "round_completed"):
            return
        progress = record.setdefault("progress", {"completed_turns": 0})
        progress.update(round=event.get("round"), phase=event.get("phase"),
                        last_progress_at=_now().isoformat(timespec="seconds"))
        agent = event.get("agent_id")
        if kind == "round_started":
            progress["rerun"] = int(event.get("rerun") or 0)
            progress["step"] = "round started"
        elif kind == "agent_started":
            progress["voter"] = agent
            progress["step"] = f"{agent} is answering"
        elif kind == "vote_received":
            vote = event.get("vote")
            progress["completed_turns"] = int(progress.get("completed_turns") or 0) + 1
            model = getattr(vote, "model", "") or "unknown model"
            failed = bool(getattr(vote, "validation_errors", None))
            value = getattr(getattr(vote, "vote", None), "value", "")
            progress["model"] = model
            progress["step"] = f"{agent} {'failed' if failed else 'answered ' + value} on {model}"
        else:
            progress["step"] = "round completed"
        try:
            _write(path, record)
        except OSError:
            pass  # progress is a courtesy; the vote goes on
    return note


def _progress_detail(record: Dict[str, Any]) -> Optional[str]:
    progress = record.get("progress") or {}
    if not progress.get("round"):
        return None
    label = (f"Rerun {progress['rerun']} (round {progress['round']})" if progress.get("rerun")
             else f"Round {progress['round']}")
    text = f"{label}, {progress.get('phase')}: {progress.get('step')}"
    try:
        minutes = int((_now() - datetime.fromisoformat(progress["last_progress_at"])).total_seconds() // 60)
        text += f"; last progress {minutes} minutes ago" if minutes else "; just now"
    except (KeyError, ValueError, TypeError):
        pass
    return text + ". Loading one voter model can take 7 to 25 minutes."


def run(ticket: str, *, jobs_dir: Path = JOBS_DIR, deliberate: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    path = _path(ticket, jobs_dir)
    record = _read(path)
    if record.get("status") != "queued":
        return record
    record.update(status="running", started_at=_now().isoformat(timespec="seconds"))
    try:
        import os
        import psutil
        record.update(worker_pid=os.getpid(), worker_started=psutil.Process(os.getpid()).create_time())
    except Exception:
        pass  # the heartbeat alone still reports the run
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
            except Exception as error:  # deliberate anyway, but leave a trace of why memory was not freed
                record["free_models_error"] = type(error).__name__
        from core.history import result_to_dict
        if record.get("submitted_by"):
            # This worker runs one deliberation; its decision record carries who asked for it.
            from core import identity
            identity.sign_in(identity.Operator(name=str(record["submitted_by"])))
        ask_owner = None if guest else _asker(path, record)
        on_event = _progress(path, record)
        if deliberate:
            import inspect
            extra = {"on_event": on_event} if "on_event" in inspect.signature(deliberate).parameters else {}
            result = deliberate(record["query"], ask_owner=ask_owner, **extra)
        else:
            result = _deliberate(record["query"], guest=guest, guest_local_only=record.get("guest_local_only"),
                                 ask_owner=ask_owner, on_event=on_event, options=record.get("options"))
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


def _deliberate(query: str, guest: bool = False, *, guest_local_only: Optional[bool] = None,
                ask_owner: Optional[Callable[[list], Optional[str]]] = None,
                on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
                options: Optional[Dict[str, Any]] = None):
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
    options = options or {}  # what a web API caller chose for this vote (theme, sequential, minimum confidence)
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    minimum_confidence = options.get("minimum_confidence")
    rules = ConsensusRules(
        minimum_confidence=config.minimum_confidence if minimum_confidence is None else float(minimum_confidence),
        quorum=config.quorum, majority=config.majority,
        high_risk_review=config.high_risk_review, evidence_threshold=config.evidence_threshold,
        classification_confidence_threshold=config.classification_confidence_threshold,
        tie_break_priority=config.tie_break_priority, proposal_taxonomy=config.proposal_taxonomy,
        monolith_domain_map=config.monolith_domain_map,
    )
    sequential = options.get("sequential")
    return Tribunal(nodes, MstyRuntime(config), rules=rules, theme_key=options.get("theme") or config.theme).deliberate(
        query, sequential=config.sequential if sequential is None else bool(sequential), guest=guest,
        ask_owner=ask_owner, on_event=on_event, source=options.get("source") or "a background vote (phone, MCP or web API)")


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m integrations.mcp.tribunal_job TICKET")
        return 2
    return 0 if run(args[0]).get("status") == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
