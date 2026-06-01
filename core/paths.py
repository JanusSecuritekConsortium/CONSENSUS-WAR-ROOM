from __future__ import annotations

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
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
HISTORY_PATH = ARBITER_DIR / "decision_history.json"
GENESIS_HISTORY_PATH = ARBITER_DIR / "decision_history_genesis.json"
BUNDLED_CONFIG_PATH = RESOURCE_ROOT / "_ARBITER" / "genesis_config.json"
OPERATOR_CONFIG_PATH = ARBITER_DIR / "genesis_config.json"
CONFIG_PATH = OPERATOR_CONFIG_PATH if OPERATOR_CONFIG_PATH.exists() or not is_frozen_runtime() else BUNDLED_CONFIG_PATH
LEGACY_HISTORY_PATH = GENESIS_HISTORY_PATH
EXPORT_DIR = ARBITER_DIR / "exports"
LOG_DIR = ARBITER_DIR / "logs"
SYSTEM_LOG_PATH = LOG_DIR / "system.jsonl"
WAR_ROOM_RUNTIME_LOG_PATH = LOG_DIR / "war_room_runtime.jsonl"
MEMORY_PATH = ARBITER_DIR / "memory" / "memory.json"
SESSION_MEMORY_PATH = ARBITER_DIR / "memory" / "session_memory.json"
CONTEXT_INDEX_PATH = ARBITER_DIR / "memory" / "context_index.json"
