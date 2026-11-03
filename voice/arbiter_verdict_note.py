"""ARBITER reads each real tribunal verdict aloud in its GLaDOS voice; AURELIUS delivers it as a Telegram voice note.

    python -m voice.arbiter_verdict_note SESSION_ID   # render and send one saved verdict

Off unless CONSENSUS_VERDICT_VOICE_NOTE=1. The tribunal starts this in its own process after the verdict is saved,
so the War Room, CLI and API never wait for the render (about a minute). ARBITER speaks; AURELIUS is only the
messenger, using the owner's existing Telegram route. Mock, simulation and test runs are never sent, and each
verdict is sent at most once. The GLaDOS voice model is English-only, so the spoken text is English; the caption
keeps the question as it was asked.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict, Optional

from core.paths import ARBITER_DIR, HISTORY_PATH

ENV_FLAG = "CONSENSUS_VERDICT_VOICE_NOTE"
LEDGER_PATH = ARBITER_DIR / "verdict_notes_sent.json"
CAPTION_LIMIT = 1024  # Telegram voice-note caption limit

VERDICT_LINES = {
    "APPROVE": "The proposal is approved.",
    "APPROVED": "The proposal is approved.",
    "CONDITIONAL_APPROVAL": "The proposal is approved, with conditions.",
    "CAUTION": "The proposal is approved, with caution.",
    "DENY": "The proposal is denied.",
    "DENIED": "The proposal is denied.",
    "NO_CONSENSUS": "No consensus was reached. The decision returns to you.",
    "DEADLOCK": "The tribunal is deadlocked. The decision returns to you.",
    "ESCALATE": "The tribunal requires your review before anything proceeds.",
    "HUMAN_REVIEW_REQUIRED": "The tribunal requires your review before anything proceeds.",
    "ABSTAIN": "The tribunal abstains. The decision returns to you.",
    "ERROR": "The deliberation failed. No verdict was reached.",
}
NUMBERS = {0: "zero", 1: "one", 2: "two", 3: "three"}


def enabled() -> bool:
    return os.environ.get(ENV_FLAG, "").strip() == "1"


def is_real(record: Dict[str, Any]) -> bool:
    """Only verdicts reached by real models outside tests; mock and simulation runs stay silent."""
    from core.history import is_real_decision
    return not os.environ.get("PYTEST_CURRENT_TEST") and bool(record.get("votes")) and is_real_decision(record)


def _sentence(text: str, limit: int = 160) -> str:
    first = re.split(r"(?<=[.!?])\s", " ".join(str(text or "").split()), maxsplit=1)[0]
    return first if len(first) <= limit else first[: limit - 1].rsplit(" ", 1)[0] + "…"


def _speakable_question(question: str) -> Optional[str]:
    """The question itself only when it is short English the voice can read; otherwise the caption carries it."""
    text = " ".join(str(question or "").split())
    if not text or len(text) > 160 or re.search(r"[^\x00-\x7F]", text):
        return None
    if re.search(r"\b(el|la|los|las|que|para|con|una|debo|deberia|deber)\b", text, re.IGNORECASE):
        return None
    return text.rstrip("?.!")


def _split_and_dissent(record: Dict[str, Any]) -> tuple[str, list[tuple[str, str, str]]]:
    votes = {agent: vote for agent, vote in (record.get("votes") or {}).items() if vote}
    counts: Dict[str, int] = {}
    for vote in votes.values():
        counts[str(vote.get("vote"))] = counts.get(str(vote.get("vote")), 0) + 1
    if not counts:
        return "", []
    majority, top = max(counts.items(), key=lambda item: item[1])
    if len(counts) == 1:
        split = f"The vote was unanimous: {NUMBERS.get(top, top)} {majority.lower()}."
    else:
        others = sum(count for value, count in counts.items() if value != majority)
        split = f"The vote was {NUMBERS.get(top, top)} to {NUMBERS.get(others, others)}."
    dissent = [(agent, str(vote.get("vote")), str(vote.get("reasoning") or ""))
               for agent, vote in sorted(votes.items()) if str(vote.get("vote")) != majority]
    return split, dissent


def script(record: Dict[str, Any]) -> str:
    """What ARBITER says: question, verdict, split, the strongest dissent and what must happen next."""
    verdict = str(record.get("verdict") or "ERROR").upper()
    question = _speakable_question(record.get("query", ""))
    parts = [f"Tribunal verdict on: {question}." if question else "Tribunal verdict on your question."]
    parts.append(VERDICT_LINES.get(verdict, f"The verdict is {verdict.lower().replace('_', ' ')}."))
    split, dissent = _split_and_dissent(record)
    if split:
        parts.append(split)
    for agent, vote, reasoning in dissent[:1]:
        reason = _sentence(reasoning)
        parts.append(f"{agent.title()} voted {vote.lower()}" + (f": {reason}" if reason else "."))
    # Stored as "AGENT: Label: what to do"; only the last part is worth hearing.
    steps = [_sentence(step.rsplit(": ", 1)[-1], 140) for step in (record.get("next_steps") or [])][:2]
    if steps:
        parts.append("Before this proceeds: " + " ".join(step if step.endswith((".", "…")) else step + "." for step in steps))
    return " ".join(parts)


def caption(record: Dict[str, Any]) -> str:
    verdict = str(record.get("verdict") or "ERROR").upper()
    split, dissent = _split_and_dissent(record)
    lines = [f"ARBITER: {verdict.replace('_', ' ')}", str(record.get("query") or "").strip()[:300]]
    if split:
        lines.append(split)
    lines += [f"{agent}: {vote}. {_sentence(reasoning, 200)}" for agent, vote, reasoning in dissent]
    lines += [f"• {step}" for step in (record.get("next_steps") or [])[:3]]
    text = "\n".join(line for line in lines if line)
    return text if len(text) <= CAPTION_LIMIT else text[: CAPTION_LIMIT - 1] + "…"


def load_record(session_id: str, history_path: Path = HISTORY_PATH) -> Optional[Dict[str, Any]]:
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    return next((item for item in reversed(history) if item.get("session_id") == session_id), None)


def render(text: str, folder: Path) -> Path:
    """GLaDOS voice to a Telegram-ready Opus file; raises when the voice or encoder is unavailable."""
    from voice.glados_adapter import GladosAdapter
    result = GladosAdapter().save_only(text)
    if not result.ok or not result.audio_path or result.mode not in ("glados_tts", "rvc"):
        raise RuntimeError(f"ARBITER voice unavailable ({result.mode})")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Local audio encoder unavailable")
    output = folder / "verdict.ogg"
    subprocess.run([ffmpeg, "-nostdin", "-y", "-i", result.audio_path, "-vn", "-ac", "1", "-c:a", "libopus",
                    "-b:a", "32k", str(output)], check=True, capture_output=True, timeout=120,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return output


def telegram_send(path: Path, text: str) -> Dict[str, Any]:
    from integrations.msty.personal import publication, spoken_briefing
    return spoken_briefing.send_voice(publication.telegram_route(), path, caption=text)


def deliver(session_id: str, *, history_path: Path = HISTORY_PATH, ledger_path: Path = LEDGER_PATH,
            render_fn: Callable[[str, Path], Path] = render,
            send_fn: Callable[[Path, str], Dict[str, Any]] = telegram_send) -> str:
    if not enabled():
        return "off"
    record = load_record(session_id, history_path)
    if record is None:
        return "not found"
    if not is_real(record):
        return "skipped: not a real-model verdict"
    sent = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
    if session_id in sent:
        return "already sent"
    with tempfile.TemporaryDirectory() as folder:
        audio = render_fn(script(record), Path(folder))
        result = send_fn(audio, caption(record))
    sent[session_id] = {"message_id": result.get("message_id"), "verdict": record.get("verdict")}
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(sent, indent=2), encoding="utf-8")
    return "sent"


def queue(result: Any) -> bool:
    """Start the voice note for a saved verdict in its own process; never blocks or fails the deliberation."""
    if not enabled() or os.environ.get("PYTEST_CURRENT_TEST") or getattr(result, "simulation", False):
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([sys.executable, "-m", "voice.arbiter_verdict_note", str(result.session_id)],
                     cwd=str(Path(__file__).resolve().parents[1]), stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    return True


def main(argv=None) -> int:
    from core.logging import log_event
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m voice.arbiter_verdict_note SESSION_ID")
        return 2
    try:
        status = deliver(args[0])
    except Exception as error:  # the system log is the only place a windowless run can report
        log_event("arbiter_verdict_note", {"session_id": args[0], "status": "failed", "error": str(error)}, level="WARN")
        return 1
    log_event("arbiter_verdict_note", {"session_id": args[0], "status": status})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
