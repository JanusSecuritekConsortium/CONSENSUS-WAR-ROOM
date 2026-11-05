from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen_runtime() -> bool:
    return bool(getattr(sys, "frozen", False))


def resolve_resource_root() -> Path:
    if is_frozen_runtime() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parents[1]


def resolve_system_root() -> Path:
    if is_frozen_runtime():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


RESOURCE_ROOT = resolve_resource_root()
SYSTEM_ROOT = resolve_system_root()


def resolve_portable_drive() -> Path:
    """The drive CONSENSUS runs from. The owner keeps everything for it (the vault, Msty, models, the private
    Aurelius store) on one portable SSD, and Windows may give that SSD a different letter on another PC, so paths
    to those things follow this drive instead of naming G:. CONSENSUS_PORTABLE_DRIVE overrides it."""
    configured = os.environ.get("CONSENSUS_PORTABLE_DRIVE", "").strip()
    return Path(configured) if configured else Path(SYSTEM_ROOT.anchor or "G:\\")


PORTABLE_DRIVE = resolve_portable_drive()


def on_portable_drive(*parts: str) -> Path:
    return PORTABLE_DRIVE.joinpath(*parts)
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
# Test runs set this (tests/conftest.py) so the deliberations they run never land in the owner's decision records.
DECISION_STORE_DIR = Path(os.environ["CONSENSUS_TEST_DECISION_DIR"]) if os.environ.get("CONSENSUS_TEST_DECISION_DIR") else ARBITER_DIR
HISTORY_PATH = DECISION_STORE_DIR / "decision_history.json"
GENESIS_HISTORY_PATH = ARBITER_DIR / "decision_history_genesis.json"
BUNDLED_CONFIG_PATH = RESOURCE_ROOT / "_ARBITER" / "genesis_config.json"
OPERATOR_CONFIG_PATH = ARBITER_DIR / "genesis_config.json"
CONFIG_PATH = OPERATOR_CONFIG_PATH if OPERATOR_CONFIG_PATH.exists() or not is_frozen_runtime() else BUNDLED_CONFIG_PATH
LEGACY_HISTORY_PATH = GENESIS_HISTORY_PATH
EXPORT_DIR = ARBITER_DIR / "exports"
LOG_DIR = ARBITER_DIR / "logs"
SYSTEM_LOG_PATH = LOG_DIR / "system.jsonl"
WAR_ROOM_RUNTIME_LOG_PATH = LOG_DIR / "war_room_runtime.jsonl"
MEMORY_PATH = DECISION_STORE_DIR / "memory" / "memory.json"
SESSION_MEMORY_PATH = DECISION_STORE_DIR / "memory" / "session_memory.json"
CONTEXT_INDEX_PATH = DECISION_STORE_DIR / "memory" / "context_index.json"
