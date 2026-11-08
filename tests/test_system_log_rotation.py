"""The system log is split by size without losing any part, and the model cache leaves no temporary file."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import logging as system_logging


def _events(path: Path) -> list:
    return [json.loads(line)["event_type"] for part in system_logging.log_files(path) for line in part.read_text(encoding="utf-8").splitlines()]


def test_a_large_log_is_renamed_and_a_new_one_started(tmp_path: Path) -> None:
    path = tmp_path / "system.jsonl"
    with mock.patch.object(system_logging, "SYSTEM_LOG_PATH", path), mock.patch.object(system_logging, "SYSTEM_LOG_MAX_BYTES", 200):
        for index in range(6):
            system_logging.log_event(f"event_{index}", {"padding": "x" * 60})

    rotated = system_logging.rotated_log_files(path)
    assert rotated, "expected at least one rotated part"
    assert path.is_file()
    assert _events(path) == [f"event_{index}" for index in range(6)]


def test_a_small_log_is_left_alone(tmp_path: Path) -> None:
    path = tmp_path / "system.jsonl"
    with mock.patch.object(system_logging, "SYSTEM_LOG_PATH", path):
        system_logging.log_event("one")
        system_logging.log_event("two")

    assert system_logging.rotated_log_files(path) == []
    assert _events(path) == ["one", "two"]


def test_a_refused_rename_keeps_appending(tmp_path: Path) -> None:
    path = tmp_path / "system.jsonl"
    path.write_text(json.dumps({"event_type": "before"}) + "\n", encoding="utf-8")
    with mock.patch.object(system_logging, "SYSTEM_LOG_PATH", path), mock.patch.object(system_logging, "SYSTEM_LOG_MAX_BYTES", 1), \
            mock.patch.object(Path, "rename", side_effect=PermissionError("in use")):
        system_logging.log_event("after")

    assert system_logging.rotated_log_files(path) == []
    assert _events(path) == ["before", "after"]


def test_the_model_cache_removes_its_temporary_file_when_the_write_fails(tmp_path: Path) -> None:
    api = pytest.importorskip("integrations.msty.api")
    target = tmp_path / "provider_model_cache.json"
    with mock.patch.object(api, "MODEL_CACHE_PATH", target), \
            mock.patch.object(Path, "replace", side_effect=PermissionError("in use")):
        with pytest.raises(PermissionError):
            api._save_model_cache({"version": 1, "entries": {}})

    assert list(tmp_path.glob("*.tmp")) == []
    assert not target.exists()


def test_the_model_cache_still_saves(tmp_path: Path) -> None:
    api = pytest.importorskip("integrations.msty.api")
    target = tmp_path / "provider_model_cache.json"
    with mock.patch.object(api, "MODEL_CACHE_PATH", target):
        api._save_model_cache({"version": 1, "entries": {"a": 1}})

    assert json.loads(target.read_text(encoding="utf-8"))["entries"] == {"a": 1}
    assert list(tmp_path.glob("*.tmp")) == []
