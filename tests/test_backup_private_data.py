from __future__ import annotations

import datetime as dt
from pathlib import Path

from tools import backup_private_data as backup


def _jobs(tmp_path: Path) -> tuple[Path, list]:
    root = tmp_path / "app"
    (root / "_ARBITER").mkdir(parents=True)
    (root / ".env").write_text("NAME=value", encoding="utf-8")
    vault = tmp_path / "vault"
    vault.mkdir()
    target = tmp_path / "backup"
    return target, backup.backup_jobs(target, root=root, vault=vault)


def test_the_backup_never_deletes_and_skips_rebuildable_audio(tmp_path):
    target, jobs = _jobs(tmp_path)
    arbiter = next(job for job in jobs if job.source.name == "_ARBITER")
    command = backup.robocopy_command(arbiter, target / "log.txt")
    assert "/E" in command and "/MIR" not in command and "/PURGE" not in command
    assert "tts_audio" in command[command.index("/XD"):]


def test_settings_are_copied_as_a_single_file(tmp_path):
    target, jobs = _jobs(tmp_path)
    settings = jobs[0]
    command = backup.robocopy_command(settings, target / "log.txt")
    assert settings.files == (".env",) and ".env" in command and "/E" not in command


def test_the_vault_is_included(tmp_path):
    target, jobs = _jobs(tmp_path)
    assert jobs[-1].name == "Obsidian vault" and jobs[-1].target == target / "Obsidian" / "vault"


def test_a_missing_drive_is_skipped_without_copying(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "drive_connected", lambda target: False)
    calls = []
    result = backup.run_backup(tmp_path / "backup", runner=lambda command: calls.append(command) or 0)
    assert result["status"] == "skipped" and calls == []


def test_results_and_a_readable_stamp_are_written(tmp_path):
    target, jobs = _jobs(tmp_path)
    codes = iter([1, 0, 9])
    result = backup.run_backup(target, jobs=jobs, runner=lambda command: next(codes, 0),
                               now=lambda: dt.datetime(2026, 11, 23, 20, 0))
    by_name = {job["name"]: job["status"] for job in result["jobs"]}
    assert by_name["settings (.env)"] == "ok"
    assert by_name["reports"] == "missing"
    assert result["status"] == "partial"
    stamp = (target / backup.STAMP_NAME).read_text(encoding="utf-8")
    assert stamp.startswith("Last backup: 2026-11-23 20:00") and "partial" in stamp


def test_without_a_target_it_explains_how_to_set_one(monkeypatch, capsys):
    monkeypatch.delenv("CONSENSUS_BACKUP_DIR", raising=False)
    assert backup.main([]) == 2
    assert "CONSENSUS_BACKUP_DIR" in capsys.readouterr().out
