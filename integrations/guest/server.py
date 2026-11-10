"""The guest door: a small password-protected API through which another AI system asks the tribunal for advice.

    python -m integrations.guest.server --new-password   # make the password to give the other system
    python -m integrations.guest.server                  # open the door (CONSENSUS_GUEST_HOST:PORT)

A guest question is a guest deliberation (core.tribunal): no personal vault brief, prior decisions or
data packets reach the voters, local models only (unless CONSENSUS_GUEST_ONLINE=1), and nothing is
saved to the owner's history or memory. The guest gets a ticket at once and asks for the verdict later;
the verdict is a summary without raw model output. One deliberation runs at a time, shared with the
owner's own tribunal jobs, and CONSENSUS_GUEST_DAILY_LIMIT caps guest questions per 24 hours.
The door listens on 127.0.0.1 unless CONSENSUS_GUEST_HOST names a private address (for example a
Tailscale one); it should never face the open internet. Full guide: docs/GUEST_DOOR.md.
"""
from __future__ import annotations

import hmac
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field

from config.version import SYSTEM_VERSION
from integrations.mcp import tribunal_job

PASSWORD_ENV = "CONSENSUS_GUEST_TOKEN"
HOST_ENV = "CONSENSUS_GUEST_HOST"
PORT_ENV = "CONSENSUS_GUEST_PORT"
LIMIT_ENV = "CONSENSUS_GUEST_DAILY_LIMIT"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8890
DEFAULT_DAILY_LIMIT = 5
MIN_PASSWORD_LENGTH = 32
MAX_QUESTION_CHARS = tribunal_job.MAX_QUERY_CHARS
WRONG_PASSWORD_DELAY = 1.0  # seconds; slows down guessing


class Question(BaseModel):  # module level: FastAPI cannot see a request model defined inside a function here
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_CHARS)


def _setting(name: str, default: str = "") -> str:
    from core.llm import online
    return online.setting(name, default)


def daily_limit() -> int:
    try:
        return max(0, int(_setting(LIMIT_ENV, str(DEFAULT_DAILY_LIMIT))))
    except ValueError:
        return DEFAULT_DAILY_LIMIT


def configured_password() -> str:
    return _setting(PASSWORD_ENV)


def new_password() -> str:
    """Make a new password, save it in .env (replacing an old one) and return it."""
    from core.llm import online
    password = secrets.token_urlsafe(32)
    online.save_settings({PASSWORD_ENV: password}, prefix="CONSENSUS_GUEST_")
    return password


def _guest_view(record: Dict[str, Any]) -> Dict[str, Any]:
    """What a guest may see of its own ticket."""
    view = {key: record[key] for key in ("ticket", "status", "requested_at", "started_at", "finished_at",
                                         "elapsed_minutes", "error", "result") if key in record}
    view["question"] = record.get("query", "")
    view["advisory_only"] = True
    return view


def create_app(*, password: Optional[str] = None, jobs_dir: Path = tribunal_job.JOBS_DIR,
               start: Callable[..., Dict[str, Any]] = tribunal_job.start,
               status: Callable[..., Dict[str, Any]] = tribunal_job.status,
               sleep: Callable[[float], None] = time.sleep):
    from fastapi import Depends, FastAPI, Header, HTTPException

    expected = password if password is not None else configured_password()
    if len(expected) < MIN_PASSWORD_LENGTH:
        raise RuntimeError("No guest password is set. Run: python -m integrations.guest.server --new-password")

    app = FastAPI(title="CONSENSUS guest door", version=SYSTEM_VERSION,
                  description="Ask the CONSENSUS tribunal for advice. Verdicts are advisory only.",
                  docs_url=None, redoc_url=None, openapi_url=None)

    def check_password(authorization: str = Header(default="")) -> None:
        supplied = authorization[7:] if authorization.lower().startswith("bearer ") else ""
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            sleep(WRONG_PASSWORD_DELAY)
            raise HTTPException(status_code=401, detail="Wrong or missing password.",
                                headers={"WWW-Authenticate": "Bearer"})

    @app.get("/guest/v1/health", dependencies=[Depends(check_password)])
    def health() -> Dict[str, Any]:
        used = tribunal_job.guest_daily_count(jobs_dir)
        return {"service": "CONSENSUS guest door", "version": SYSTEM_VERSION,
                "busy": tribunal_job.deliberation_running(jobs_dir),
                "questions_left_today": max(0, daily_limit() - used)}

    @app.post("/guest/v1/deliberations", status_code=202, dependencies=[Depends(check_password)])
    def deliberate(body: Question) -> Dict[str, Any]:
        if tribunal_job.guest_daily_count(jobs_dir) >= daily_limit():
            raise HTTPException(status_code=429, detail="The daily limit of guest questions is reached.")
        try:
            started = start(body.question, jobs_dir=jobs_dir, guest=True)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if started.get("status") == "busy":
            raise HTTPException(status_code=409, detail=started["detail"])
        if started.get("status") != "queued":
            raise HTTPException(status_code=503, detail=started.get("detail", "The tribunal cannot start now."))
        return {"ticket": started["ticket"], "status": "queued",
                "detail": "The tribunal is deliberating; on local models this can take up to an hour. "
                          "Ask for the verdict with GET /guest/v1/deliberations/{ticket}."}

    @app.get("/guest/v1/deliberations/{ticket}", dependencies=[Depends(check_password)])
    def verdict(ticket: str) -> Dict[str, Any]:
        try:
            record = status(ticket, jobs_dir=jobs_dir)
        except ValueError:
            record = {}
        if not record.get("guest"):  # the owner's own tickets do not exist for a guest
            raise HTTPException(status_code=404, detail="Unknown ticket.")
        return _guest_view(record)

    return app


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="CONSENSUS guest door (docs/GUEST_DOOR.md).")
    parser.add_argument("--new-password", action="store_true",
                        help="make a new guest password, save it in .env and print it once")
    args = parser.parse_args(argv)
    if args.new_password:
        print("New guest password (saved in .env; give it only to the other system's owner):")
        print(new_password())
        return 0
    try:
        app = create_app()
    except RuntimeError as error:
        print(error)
        return 1
    import uvicorn
    host = _setting(HOST_ENV, DEFAULT_HOST) or DEFAULT_HOST
    try:
        port = int(_setting(PORT_ENV, str(DEFAULT_PORT)))
    except ValueError:
        port = DEFAULT_PORT
    print(f"CONSENSUS guest door open on http://{host}:{port}/guest/v1/ (Ctrl+C closes it)")
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
