from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logging import log_error, log_event
from core.paths import MEMORY_PATH


DEFAULT_MEMORY_PATH = MEMORY_PATH


class MemoryStoreError(RuntimeError):
    pass


class MemoryStore:
    """Unified JSON memory store for user, Arbiter, and monolith context."""

    def __init__(self, path: Path = DEFAULT_MEMORY_PATH):
        self.path = path

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            backup_path = self._backup_corrupt_file()
            error = MemoryStoreError(f"Memory JSON is corrupt. Backup written to: {backup_path}")
            log_error("memory_corruption", exc, {"path": str(self.path), "backup_path": str(backup_path)})
            raise error from exc
        except OSError as exc:
            log_error("memory_load_error", exc, {"path": str(self.path)})
            raise MemoryStoreError(f"Unable to read memory store: {self.path}") from exc
        if not isinstance(loaded, dict):
            backup_path = self._backup_corrupt_file()
            error = MemoryStoreError(f"Memory root must be a JSON object. Backup written to: {backup_path}")
            log_event("memory_invalid_shape", {"path": str(self.path), "backup_path": str(backup_path)}, level="ERROR")
            raise error
        return self._normalize(loaded)

    def save(self, memory: Dict[str, Any]) -> None:
        if not isinstance(memory, dict):
            raise MemoryStoreError("Memory store payload must be a dictionary.")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(self._normalize(memory), handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, self.path)
            log_event("memory_write", {"path": str(self.path)})
        except OSError as exc:
            log_error("memory_write_error", exc, {"path": str(self.path), "tmp_path": str(tmp_path)})
            raise MemoryStoreError(f"Unable to write memory store: {self.path}") from exc
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def append_decision_context(
        self,
        session_id: str,
        verdict: str,
        summary: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        memory = self.load()
        memory.setdefault("decisions", []).append(
            {
                "session_id": session_id,
                "verdict": verdict,
                "summary": summary,
                "tags": tags or [],
                "timestamp": datetime.now().isoformat(),
            }
        )
        memory["decisions"] = memory["decisions"][-500:]
        self.save(memory)
        return memory

    @staticmethod
    def _empty() -> Dict[str, Any]:
        return {
            "user": {},
            "agents": {
                "ARBITER": {},
                "RATIONALIS": {},
                "AETERNUM": {},
                "BELLATOR": {},
                "AURELIUS": {},
            },
            "monoliths": {
                "RATIONALIS": {},
                "AETERNUM": {},
                "BELLATOR": {},
            },
            "decisions": [],
        }

    def _backup_corrupt_file(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.path.with_name(f"{self.path.stem}.corrupt.{timestamp}{self.path.suffix}")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(self.path, backup_path)
        except OSError as exc:
            log_error("memory_backup_error", exc, {"path": str(self.path), "backup_path": str(backup_path)})
            raise MemoryStoreError(f"Unable to back up corrupt memory store: {self.path}") from exc
        return backup_path

    @classmethod
    def _normalize(cls, memory: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cls._empty()
        normalized.update(memory)
        agents = normalized.get("agents")
        if not isinstance(agents, dict):
            agents = {}
        for agent_id in ["ARBITER", "RATIONALIS", "AETERNUM", "BELLATOR", "AURELIUS"]:
            agents.setdefault(agent_id, {})
        normalized["agents"] = agents

        monoliths = normalized.get("monoliths")
        if not isinstance(monoliths, dict):
            monoliths = {}
        for agent_id in ["RATIONALIS", "AETERNUM", "BELLATOR"]:
            monoliths.setdefault(agent_id, agents.get(agent_id, {}))
        normalized["monoliths"] = monoliths

        if not isinstance(normalized.get("decisions"), list):
            normalized["decisions"] = []
        if not isinstance(normalized.get("user"), dict):
            normalized["user"] = {}
        return normalized
