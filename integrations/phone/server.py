"""The phone page: a small web page for submitting a proposal and reading verdicts from a phone.

    python -m integrations.phone.server      # or tools\\launchers\\start_phone_page.cmd

People sign in with their CONSENSUS operator profile and PIN (docs/OPERATOR_LOCK.md); there is no
separate password. A proposal becomes an ordinary tribunal ticket (integrations.mcp.tribunal_job)
with the operator's name on it, so one deliberation runs at a time, shared with every other entry.
The page lists only tickets submitted through it, with a verdict summary and no raw model output.

It listens on 127.0.0.1 unless CONSENSUS_PHONE_HOST names a private address; "tailscale" picks this
PC's Tailscale address. It must never face the open internet: the connection is plain HTTP and a
PIN is short. Full guide: docs/PHONE_ACCESS.md.
"""
from __future__ import annotations

import secrets
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import Response  # module level: route annotations are resolved from here
from pydantic import BaseModel, Field

from config.version import SYSTEM_VERSION
from core import identity
from core.identity.store import IdentityError, PIN_MAX_LENGTH
from integrations.mcp import tribunal_job

HOST_ENV = "CONSENSUS_PHONE_HOST"
PORT_ENV = "CONSENSUS_PHONE_PORT"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8891
COOKIE = "consensus_phone"
SESSION_SECONDS = 12 * 60 * 60
MAX_SESSIONS = 64
WRONG_PIN_DELAY = 1.0  # seconds, on top of the growing wait kept with the profile
RECENT_LIMIT = 20
MAX_QUESTION_CHARS = tribunal_job.MAX_QUERY_CHARS


class Login(BaseModel):  # module level: FastAPI cannot see a request model defined inside a function here
    name: str = Field(..., min_length=1, max_length=64)
    pin: str = Field(..., min_length=1, max_length=PIN_MAX_LENGTH)


class Proposal(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_CHARS)


class Sessions:
    """Who is signed in on which phone. Kept in memory: closing the page server signs everyone out."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions: Dict[str, tuple[str, float]] = {}

    def open(self, name: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            now = self._clock()
            self._sessions = {key: value for key, value in self._sessions.items() if value[1] > now}
            while len(self._sessions) >= MAX_SESSIONS:
                self._sessions.pop(min(self._sessions, key=lambda key: self._sessions[key][1]))
            self._sessions[token] = (name, now + SESSION_SECONDS)
        return token

    def name(self, token: str) -> Optional[str]:
        with self._lock:
            entry = self._sessions.get(token or "")
            if entry is None or entry[1] <= self._clock():
                self._sessions.pop(token or "", None)
                return None
            return entry[0]

    def close(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token or "", None)


def _view(record: Dict[str, Any]) -> Dict[str, Any]:
    view = {key: record[key] for key in ("ticket", "status", "requested_at", "started_at", "finished_at",
                                         "elapsed_minutes", "error", "submitted_by") if key in record}
    view["question"] = record.get("query", "")
    result = record.get("result")
    if isinstance(result, dict):
        view["result"] = {key: result.get(key) for key in ("verdict", "confidence", "reason", "next_steps")}
    return view


def recent_phone_tickets(jobs_dir: Path, status: Callable[..., Dict[str, Any]], limit: int = RECENT_LIMIT) -> List[Dict[str, Any]]:
    """Tickets submitted through the phone page, newest first. Guest tickets and the owner's
    desktop or MCP tickets carry no operator name and are not listed."""
    records = []
    for path in sorted(jobs_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            record = status(path.stem, jobs_dir=jobs_dir)
        except (ValueError, OSError):
            continue
        if record.get("submitted_by") and not record.get("guest"):
            records.append(record)
    records.sort(key=lambda record: str(record.get("requested_at", "")), reverse=True)
    return [_view(record) for record in records[:limit]]


def create_app(*, jobs_dir: Path = tribunal_job.JOBS_DIR,
               start: Callable[..., Dict[str, Any]] = tribunal_job.start,
               status: Callable[..., Dict[str, Any]] = tribunal_job.status,
               sleep: Callable[[float], None] = time.sleep,
               sessions: Optional[Sessions] = None):
    from fastapi import Cookie, Depends, FastAPI, HTTPException
    from fastapi.responses import HTMLResponse

    from integrations.phone.page import PAGE

    try:
        if not identity.lock_enabled():
            raise RuntimeError("No operator profiles exist. Create one first: tools\\launchers\\manage_users.cmd")
    except IdentityError as error:
        raise RuntimeError(str(error)) from error

    sessions = sessions or Sessions()
    app = FastAPI(title="CONSENSUS phone page", version=SYSTEM_VERSION, docs_url=None, redoc_url=None, openapi_url=None)

    def signed_in(consensus_phone: str = Cookie(default="")) -> str:
        name = sessions.name(consensus_phone)
        # A profile removed while its phone is still signed in loses access at once.
        if name is None or identity.find_operator(name) is None:
            raise HTTPException(status_code=401, detail="Sign in first.")
        return name

    @app.get("/", response_class=HTMLResponse)
    def page() -> HTMLResponse:
        return HTMLResponse(PAGE, headers={
            "Cache-Control": "no-store",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                       "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        })

    @app.get("/phone/v1/operators")
    def operators() -> Dict[str, Any]:
        # The same names the boot window lists; needed to offer the sign-in choice.
        return {"operators": [operator.name for operator in identity.list_operators()]}

    @app.post("/phone/v1/login")
    def login(body: Login, response: Response) -> Dict[str, Any]:
        check = identity.verify_pin(body.name, body.pin)
        if not check.ok or check.operator is None:
            sleep(WRONG_PIN_DELAY)
            raise HTTPException(status_code=401, detail=check.message or "Name or PIN not recognised.")
        response.set_cookie(COOKIE, sessions.open(check.operator.name), max_age=SESSION_SECONDS,
                            httponly=True, samesite="strict", path="/")
        return {"name": check.operator.name}

    @app.post("/phone/v1/logout")
    def logout(response: Response, consensus_phone: str = Cookie(default="")) -> Dict[str, Any]:
        sessions.close(consensus_phone)
        response.delete_cookie(COOKIE, path="/")
        return {"signed_out": True}

    @app.get("/phone/v1/me")
    def me(name: str = Depends(signed_in)) -> Dict[str, Any]:
        return {"name": name}

    @app.post("/phone/v1/proposals", status_code=202)
    def submit(body: Proposal, name: str = Depends(signed_in)) -> Dict[str, Any]:
        try:
            started = start(body.question, jobs_dir=jobs_dir, submitted_by=name)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if started.get("status") == "busy":
            raise HTTPException(status_code=409, detail="The tribunal is busy with another deliberation; try again later.")
        if started.get("status") != "queued":
            raise HTTPException(status_code=503, detail=started.get("detail", "The tribunal cannot start now."))
        return {"ticket": started["ticket"], "status": "queued"}

    @app.get("/phone/v1/proposals")
    def proposals(name: str = Depends(signed_in)) -> Dict[str, Any]:
        return {"proposals": recent_phone_tickets(jobs_dir, status)}

    return app


def tailscale_address(run: Callable[..., Any] = subprocess.run) -> str:
    """This PC's Tailscale IPv4 address, or "" when Tailscale is not installed or not connected."""
    try:
        completed = run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    lines = completed.stdout.split() if completed.returncode == 0 else []
    return lines[0] if lines and lines[0].startswith("100.") else ""


def resolve_host(configured: str, find_tailscale: Callable[[], str] = tailscale_address) -> str:
    configured = (configured or "").strip()
    if configured.lower() == "tailscale":
        address = find_tailscale()
        if not address:
            raise RuntimeError("Tailscale is not installed or not connected on this PC (docs/PHONE_ACCESS.md).")
        return address
    if configured in {"0.0.0.0", "::"}:
        raise RuntimeError("The phone page does not listen on every network. Use 'tailscale' or one private address.")
    return configured or DEFAULT_HOST


def main(argv=None) -> int:
    import argparse

    from core.llm import online

    parser = argparse.ArgumentParser(description="CONSENSUS phone page (docs/PHONE_ACCESS.md).")
    parser.add_argument("--host", default=None, help="address to listen on; 'tailscale' picks this PC's Tailscale address")
    args = parser.parse_args(argv)
    try:
        host = resolve_host(args.host if args.host is not None else online.setting(HOST_ENV, DEFAULT_HOST))
        app = create_app()
    except RuntimeError as error:
        print(error)
        return 1
    try:
        port = int(online.setting(PORT_ENV, str(DEFAULT_PORT)))
    except ValueError:
        port = DEFAULT_PORT
    import uvicorn
    print(f"CONSENSUS phone page open on http://{host}:{port}/ (Ctrl+C closes it)")
    if host == DEFAULT_HOST:
        print("Only this PC can reach it. For the phone, see docs/PHONE_ACCESS.md.")
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
