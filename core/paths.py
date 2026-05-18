from __future__ import annotations

from pathlib import Path

SYSTEM_ROOT = Path(__file__).resolve().parents[1]
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
HISTORY_PATH = ARBITER_DIR / "decision_history.json"
GENESIS_HISTORY_PATH = ARBITER_DIR / "decision_history_genesis.json"
CONFIG_PATH = ARBITER_DIR / "genesis_config.json"
LEGACY_HISTORY_PATH = GENESIS_HISTORY_PATH
EXPORT_DIR = ARBITER_DIR / "exports"
LOG_DIR = ARBITER_DIR / "logs"
SYSTEM_LOG_PATH = LOG_DIR / "system.jsonl"
WAR_ROOM_RUNTIME_LOG_PATH = LOG_DIR / "war_room_runtime.log"
MEMORY_PATH = ARBITER_DIR / "memory" / "memory.json"
SESSION_MEMORY_PATH = ARBITER_DIR / "memory" / "session_memory.json"
CONTEXT_INDEX_PATH = ARBITER_DIR / "memory" / "context_index.json"
