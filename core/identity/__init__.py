"""Who is operating CONSENSUS: profiles, the PIN lock and the signed-in operator."""
from __future__ import annotations

import threading

from core.identity.store import (
    IdentityError,
    Operator,
    PinCheck,
    add_operator,
    change_pin,
    find_operator,
    list_operators,
    lock_enabled,
    remove_operator,
    set_windows_hello,
    verify_pin,
)

_session_lock = threading.Lock()
_current: Operator | None = None


def sign_in(operator: Operator | None) -> None:
    """Record who unlocked this run of the application (None signs out)."""
    global _current
    with _session_lock:
        _current = operator


def current_operator() -> Operator | None:
    with _session_lock:
        return _current


def current_operator_name() -> str | None:
    operator = current_operator()
    return operator.name if operator is not None else None


__all__ = [
    "IdentityError",
    "Operator",
    "PinCheck",
    "add_operator",
    "change_pin",
    "current_operator",
    "current_operator_name",
    "find_operator",
    "list_operators",
    "lock_enabled",
    "remove_operator",
    "set_windows_hello",
    "sign_in",
    "verify_pin",
]
