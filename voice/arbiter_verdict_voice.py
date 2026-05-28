from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.logging import log_event
from core.paths import SYSTEM_LOG_PATH
from voice.glados_adapter import GladosAdapter


ARBITER_VOICE_PROFILE = "ARBITER_GLADOS"
ARBITER_VOICE_EVENT = "arbiter_verdict_voice_dispatch"
_DISPATCHED_PROPOSALS: set[str] = set()
_DISPATCH_LOCK = threading.Lock()


@dataclass(frozen=True)
class ArbiterVoiceDispatch:
    proposal_id: str
    verdict: str
    terminal_state: str
    text: str
    backend: str = ARBITER_VOICE_PROFILE
    status: str = "queued"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    audio_path: str | None = None
    degraded_reason: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "verdict": self.verdict,
            "terminal_state": self.terminal_state,
            "text": self.text,
            "backend": self.backend,
            "status": self.status,
            "timestamp": self.timestamp,
            "audio_path": self.audio_path,
            "degraded_reason": self.degraded_reason,
        }


def reset_arbiter_voice_dispatch_cache() -> None:
    with _DISPATCH_LOCK:
        _DISPATCHED_PROPOSALS.clear()


def terminal_state_for_result(result: Any) -> str:
    verdict = str(getattr(getattr(result, "verdict", "ERROR"), "value", getattr(result, "verdict", "ERROR"))).upper()
    terminal_branch = str(getattr(result, "terminal_branch", "") or "").upper()
    triggers = " ".join(str(item).upper() for item in (getattr(result, "review_triggers", []) or []))
    taxonomy = getattr(result, "proposal_classification", {}) or {}
    taxonomy_status = str(taxonomy.get("status", "") if isinstance(taxonomy, dict) else "").upper()
    taxonomy_reason = str(taxonomy.get("reason", "") if isinstance(taxonomy, dict) else "").upper()

    if "CLASSIFICATION_FAILURE" in terminal_branch or "CLASSIFICATION_FAILURE" in triggers:
        return "CLASSIFICATION_FAILURE"
    if taxonomy_status == "FAILED" or "CLASSIF" in taxonomy_reason:
        return "CLASSIFICATION_FAILURE"
    if verdict == "NO_CONSENSUS" or "NO_CONSENSUS" in terminal_branch:
        return "NO_CONSENSUS"
    if verdict in {"ESCALATE", "HUMAN_REVIEW_REQUIRED"} or "ESCALAT" in terminal_branch or "ESCALAT" in triggers:
        return "ESCALATION_REQUIRED"
    if verdict in {"DENY", "DENIED"}:
        return "DENY"
    if verdict in {"APPROVE", "APPROVED"}:
        return "CONSENSUS_REACHED"
    if verdict == "ERROR":
        return "ERROR"
    if verdict in {"ABSTAIN", "DEADLOCK"}:
        return "NO_CONSENSUS"
    return verdict or "ERROR"


def announcement_text_for_state(terminal_state: str, verdict: str = "") -> str:
    state = terminal_state.upper()
    if state == "NO_CONSENSUS":
        return "Tribunal deadlock. No consensus reached. Manual review recommended."
    if state == "CLASSIFICATION_FAILURE":
        return "Classification failure. Proposal taxonomy could not be resolved. Escalating to operator review."
    if state == "ESCALATION_REQUIRED":
        return "Escalation required. Tribunal confidence insufficient for autonomous verdict."
    if state == "CONSENSUS_REACHED":
        normalized_verdict = verdict.upper()
        if normalized_verdict in {"DENY", "DENIED"}:
            return "Consensus reached. Proposal denied."
        return "Consensus reached. Proposal approved."
    if state == "DENY":
        return "Consensus reached. Proposal denied."
    if state == "ERROR":
        return "Tribunal error. Decision pipeline failed."
    if state == "EXPORT_READY":
        return "Verdict export ready. Tribunal record sealed."
    return "Tribunal terminal state reached. Operator review recommended."


def build_arbiter_voice_dispatch(result: Any) -> ArbiterVoiceDispatch:
    verdict = str(getattr(getattr(result, "verdict", "ERROR"), "value", getattr(result, "verdict", "ERROR"))).upper()
    proposal_id = str(getattr(result, "session_id", "") or getattr(result, "proposal_id", "") or "unknown")
    terminal_state = terminal_state_for_result(result)
    return ArbiterVoiceDispatch(
        proposal_id=proposal_id,
        verdict=verdict,
        terminal_state=terminal_state,
        text=announcement_text_for_state(terminal_state, verdict),
    )


def dispatch_arbiter_verdict_voice(
    result: Any,
    *,
    async_dispatch: bool = True,
    enabled: bool = True,
    adapter_factory: Callable[[], Any] | None = None,
) -> ArbiterVoiceDispatch:
    dispatch = build_arbiter_voice_dispatch(result)
    if not enabled:
        disabled = _replace_dispatch(dispatch, status="disabled", degraded_reason="arbiter voice disabled")
        _log_dispatch(disabled)
        return disabled

    with _DISPATCH_LOCK:
        if dispatch.proposal_id in _DISPATCHED_PROPOSALS:
            duplicate = _replace_dispatch(dispatch, status="duplicate_suppressed")
            _log_dispatch(duplicate)
            return duplicate
        _DISPATCHED_PROPOSALS.add(dispatch.proposal_id)

    _log_dispatch(dispatch)
    if async_dispatch:
        thread = threading.Thread(
            target=_speak_dispatch,
            args=(dispatch, adapter_factory),
            name=f"arbiter-voice-{dispatch.proposal_id}",
            daemon=True,
        )
        thread.start()
        return dispatch
    return _speak_dispatch(dispatch, adapter_factory)


def voice_status_snapshot(path: Path = SYSTEM_LOG_PATH) -> Dict[str, Any]:
    last = read_last_voice_announcement(path)
    if last is None:
        return {
            "profile": ARBITER_VOICE_PROFILE,
            "backend": ARBITER_VOICE_PROFILE,
            "status": "ENABLED",
            "last_voice_announcement": None,
        }
    status = str((last or {}).get("status") or "unknown")
    if status in {"success", "queued"}:
        state = "enabled"
    elif status == "degraded":
        state = "degraded"
    elif status in {"failed", "disabled"}:
        state = status
    else:
        state = "unknown"
    return {
        "profile": ARBITER_VOICE_PROFILE,
        "backend": ARBITER_VOICE_PROFILE,
        "status": state.upper(),
        "last_voice_announcement": last,
    }


def read_last_voice_announcement(path: Path = SYSTEM_LOG_PATH) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("event_type") != ARBITER_VOICE_EVENT:
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            return {"timestamp": record.get("timestamp"), **payload}
    return None


def _speak_dispatch(dispatch: ArbiterVoiceDispatch, adapter_factory: Callable[[], Any] | None = None) -> ArbiterVoiceDispatch:
    try:
        adapter = adapter_factory() if adapter_factory is not None else GladosAdapter()
        rendered = adapter.speak(dispatch.text)
        mode = str(getattr(rendered, "mode", "unknown"))
        audio_path = getattr(rendered, "audio_path", None)
        metadata = getattr(rendered, "metadata", {}) or {}
        if bool(getattr(rendered, "ok", False)):
            if mode in {"rvc", "glados_tts"}:
                completed = _replace_dispatch(dispatch, status="success", audio_path=audio_path)
            else:
                completed = _replace_dispatch(
                    dispatch,
                    status="degraded",
                    audio_path=audio_path,
                    degraded_reason=f"configured fallback backend used: {mode}",
                )
            _log_dispatch(completed, {"mode": mode, **metadata})
            return completed
        failed = _replace_dispatch(
            dispatch,
            status="failed",
            audio_path=audio_path,
            degraded_reason=str(metadata.get("error") or "voice backend failed"),
        )
        _log_dispatch(failed, {"mode": mode, **metadata}, level="WARN")
        return failed
    except Exception as exc:
        failed = _replace_dispatch(dispatch, status="failed", degraded_reason=str(exc))
        _log_dispatch(failed, level="WARN")
        return failed


def _replace_dispatch(
    dispatch: ArbiterVoiceDispatch,
    *,
    status: str,
    audio_path: str | None = None,
    degraded_reason: str | None = None,
) -> ArbiterVoiceDispatch:
    return ArbiterVoiceDispatch(
        proposal_id=dispatch.proposal_id,
        verdict=dispatch.verdict,
        terminal_state=dispatch.terminal_state,
        text=dispatch.text,
        backend=dispatch.backend,
        status=status,
        audio_path=audio_path,
        degraded_reason=degraded_reason,
    )


def _log_dispatch(dispatch: ArbiterVoiceDispatch, metadata: Dict[str, Any] | None = None, level: str = "INFO") -> None:
    payload = dispatch.as_dict()
    if metadata:
        payload["metadata"] = metadata
    log_event(ARBITER_VOICE_EVENT, payload, level=level)


__all__ = [
    "ARBITER_VOICE_EVENT",
    "ARBITER_VOICE_PROFILE",
    "ArbiterVoiceDispatch",
    "announcement_text_for_state",
    "build_arbiter_voice_dispatch",
    "dispatch_arbiter_verdict_voice",
    "read_last_voice_announcement",
    "reset_arbiter_voice_dispatch_cache",
    "terminal_state_for_result",
    "voice_status_snapshot",
]
