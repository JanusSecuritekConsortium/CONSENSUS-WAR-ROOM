"""Operator profiles and their PINs.

The lock is off until the first profile is created. A PIN is never stored: the
file keeps a salted scrypt digest, so reading the file does not reveal the PIN.
This is a door lock for the application, not encryption of the records on disk.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.paths import SYSTEM_ROOT, is_frozen_runtime

def default_users_path(system_root: Path = SYSTEM_ROOT, frozen: bool | None = None) -> Path:
    """Where the profiles live. CONSENSUS.exe inside the project's dist folder shares the project's
    file, so the desktop lock and the services run from source (the phone page) know the same
    people. An exe copied anywhere else keeps its own file beside it."""
    configured = os.environ.get("CONSENSUS_USERS_FILE")
    if configured:
        return Path(configured)
    frozen = is_frozen_runtime() if frozen is None else frozen
    project = system_root.parent / "_ARBITER"
    if frozen and system_root.name.lower() == "dist" and project.is_dir():
        return project / "users.json"
    return system_root / "_ARBITER" / "users.json"


USERS_PATH = default_users_path()
ROLES = ("owner", "operator")
PIN_MIN_LENGTH = 4
PIN_MAX_LENGTH = 64
NAME_MAX_LENGTH = 32
FREE_ATTEMPTS = 3  # wrong PINs before a wait is imposed
MAX_WAIT_SECONDS = 300
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
_lock = threading.RLock()


class IdentityError(ValueError):
    """A profile request that cannot be carried out; the message is safe to show."""


@dataclass(frozen=True)
class Operator:
    name: str
    role: str = "operator"
    windows_hello: bool = False


@dataclass(frozen=True)
class PinCheck:
    ok: bool
    operator: Operator | None = None
    wait_seconds: int = 0
    message: str = ""


def _digest(pin: str, salt: bytes) -> str:
    return hashlib.scrypt(pin.encode("utf-8"), salt=salt, **_SCRYPT).hex()


def _read(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"users": []}
    except (OSError, ValueError) as exc:
        # An unreadable file must not silently switch the lock off.
        raise IdentityError(f"The operator file cannot be read: {path}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        raise IdentityError(f"The operator file is damaged: {path}")
    return data


def _write(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _find(data: Dict[str, Any], name: str) -> Dict[str, Any] | None:
    wanted = name.strip().casefold()
    for user in data["users"]:
        if isinstance(user, dict) and str(user.get("name", "")).casefold() == wanted:
            return user
    return None


def _operator(user: Dict[str, Any]) -> Operator:
    role = user.get("role") if user.get("role") in ROLES else "operator"
    return Operator(name=str(user.get("name", "")), role=role, windows_hello=bool(user.get("windows_hello")))


def _clean_name(name: str) -> str:
    cleaned = " ".join(str(name).split())
    if not cleaned:
        raise IdentityError("A profile needs a name.")
    if len(cleaned) > NAME_MAX_LENGTH:
        raise IdentityError(f"A profile name can have at most {NAME_MAX_LENGTH} characters.")
    if not all(character.isalnum() or character in " -_." for character in cleaned):
        raise IdentityError("A profile name can use letters, digits, spaces, hyphens, underscores and dots.")
    return cleaned


def _check_pin_shape(pin: str) -> None:
    if not PIN_MIN_LENGTH <= len(pin) <= PIN_MAX_LENGTH:
        raise IdentityError(f"A PIN needs {PIN_MIN_LENGTH} to {PIN_MAX_LENGTH} characters.")
    if len(set(pin)) == 1:
        raise IdentityError("A PIN cannot be one character repeated.")


def _set_pin(user: Dict[str, Any], pin: str) -> None:
    _check_pin_shape(pin)
    salt = secrets.token_bytes(16)
    user.update(salt=salt.hex(), pin_digest=_digest(pin, salt), failed_attempts=0, locked_until=0)


def list_operators(path: Path | None = None) -> List[Operator]:
    with _lock:
        return [_operator(user) for user in _read(path or USERS_PATH)["users"] if isinstance(user, dict)]


def lock_enabled(path: Path | None = None) -> bool:
    """The application asks for a PIN once at least one profile exists."""
    return bool(list_operators(path))


def add_operator(name: str, pin: str, role: str = "operator", path: Path | None = None) -> Operator:
    target = path or USERS_PATH
    with _lock:
        data = _read(target)
        cleaned = _clean_name(name)
        if _find(data, cleaned) is not None:
            raise IdentityError(f"A profile named {cleaned} already exists.")
        # The first profile owns the installation; someone must be able to manage the others.
        if not data["users"]:
            role = "owner"
        if role not in ROLES:
            raise IdentityError(f"Unknown role: {role}")
        user: Dict[str, Any] = {"name": cleaned, "role": role, "windows_hello": False,
                                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _set_pin(user, pin)
        data["users"].append(user)
        _write(data, target)
        return _operator(user)


def change_pin(name: str, pin: str, path: Path | None = None) -> None:
    target = path or USERS_PATH
    with _lock:
        data = _read(target)
        user = _find(data, name)
        if user is None:
            raise IdentityError(f"No profile named {name}.")
        _set_pin(user, pin)
        _write(data, target)


def set_windows_hello(name: str, enabled: bool, path: Path | None = None) -> None:
    target = path or USERS_PATH
    with _lock:
        data = _read(target)
        user = _find(data, name)
        if user is None:
            raise IdentityError(f"No profile named {name}.")
        user["windows_hello"] = bool(enabled)
        _write(data, target)


def remove_operator(name: str, path: Path | None = None) -> None:
    target = path or USERS_PATH
    with _lock:
        data = _read(target)
        user = _find(data, name)
        if user is None:
            raise IdentityError(f"No profile named {name}.")
        others = [item for item in data["users"] if item is not user]
        if others and user.get("role") == "owner" and not any(item.get("role") == "owner" for item in others):
            raise IdentityError("The last owner cannot be removed while other profiles exist.")
        data["users"] = others
        _write(data, target)


def find_operator(name: str, path: Path | None = None) -> Operator | None:
    with _lock:
        user = _find(_read(path or USERS_PATH), name)
        return _operator(user) if user is not None else None


def verify_pin(name: str, pin: str, path: Path | None = None, now: float | None = None) -> PinCheck:
    """Check a PIN. Wrong PINs beyond the free attempts impose a growing wait,
    which is kept in the file so restarting the application does not clear it."""
    target = path or USERS_PATH
    moment = time.time() if now is None else now
    with _lock:
        data = _read(target)
        user = _find(data, name)
        if user is None:
            # Spend the same effort as a real check so a wrong name is not quicker than a wrong PIN.
            _digest(pin, b"\x00" * 16)
            return PinCheck(False, message="Name or PIN not recognised.")
        remaining = int(float(user.get("locked_until") or 0) - moment)
        if remaining > 0:
            return PinCheck(False, wait_seconds=remaining, message=f"Too many wrong PINs. Wait {remaining} seconds.")
        try:
            expected = _digest(pin, bytes.fromhex(str(user.get("salt", ""))))
        except ValueError:
            return PinCheck(False, message="This profile is damaged; ask the owner to set its PIN again.")
        if hmac.compare_digest(expected, str(user.get("pin_digest", ""))):
            if user.get("failed_attempts") or user.get("locked_until"):
                user.update(failed_attempts=0, locked_until=0)
                _write(data, target)
            return PinCheck(True, operator=_operator(user))
        failed = int(user.get("failed_attempts") or 0) + 1
        wait = 0
        if failed >= FREE_ATTEMPTS:
            wait = min(MAX_WAIT_SECONDS, 5 * 2 ** (failed - FREE_ATTEMPTS))
        user.update(failed_attempts=failed, locked_until=moment + wait if wait else 0)
        _write(data, target)
        message = f"Too many wrong PINs. Wait {wait} seconds." if wait else "Name or PIN not recognised."
        return PinCheck(False, wait_seconds=wait, message=message)
