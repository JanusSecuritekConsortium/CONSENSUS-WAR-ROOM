"""Tribunal deliberations requested over the CONSENSUS MCP connection, run in their own process.

    python -m integrations.mcp.tribunal_job TICKET   # run the deliberation saved under TICKET

A deliberation takes minutes on local models, longer than an MCP call waits, so `start` saves the question as a
job record, launches this module detached and returns a ticket; `status` reads the record. One deliberation runs
at a time because the voters share one GPU. Records live in the git-ignored _ARBITER/memory folder.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
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


def _launch(ticket: str) -> None:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([sys.executable, "-m", "integrations.mcp.tribunal_job", ticket],
                     cwd=str(Path(__file__).resolve().parents[2]), stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)


def start(query: str, *, jobs_dir: Path = JOBS_DIR, launch: Callable[[str], None] = _launch) -> Dict[str, Any]:
    query = " ".join(str(query or "").split())
    if not query:
        raise ValueError("A question is required")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"Questions are limited to {MAX_QUERY_CHARS} characters")
    from core.history import unfilled_template_fields
    blanks = unfilled_template_fields(query)
    if len(blanks) >= 2:
        raise ValueError("The question is an unfilled template; fill in " + ", ".join(blanks) + " first")
    busy = _running(jobs_dir)
    if busy:
        return {"status": "busy", "ticket": busy["ticket"],
                "detail": "Another deliberation is running; ask again when tribunal_verdict reports it finished."}
    ticket = uuid.uuid4().hex[:12]
    record = {"ticket": ticket, "query": query, "status": "queued", "requested_at": _now().isoformat(timespec="seconds")}
    _write(_path(ticket, jobs_dir), record)
    launch(ticket)
    return {"status": "queued", "ticket": ticket,
            "detail": "The tribunal is deliberating; this usually takes several minutes. Check with tribunal_verdict."}


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
        from core.history import result_to_dict
        result = (deliberate or _deliberate)(record["query"])
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


def _deliberate(query: str):
    """The same tribunal the command line builds from the runtime config."""
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
    return Tribunal(nodes, MstyRuntime(config), rules=rules, theme_key=config.theme).deliberate(query, sequential=config.sequential)


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m integrations.mcp.tribunal_job TICKET")
        return 2
    return 0 if run(args[0]).get("status") == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
