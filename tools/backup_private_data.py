"""Copy the owner's own CONSENSUS data to a backup drive.

The code is on GitHub and the AI models can be downloaded again, so this copies only what cannot be
replaced: settings (.env), vote records and other files in _ARBITER, reports and logs, voice models
and the Obsidian vault. It only adds and updates files; it never deletes anything on the backup
drive. When the drive is not connected it does nothing and says so.

    python tools/backup_private_data.py --target I:\\Backup\\CONSENSUS_DATA
    (or set CONSENSUS_BACKUP_DIR and run it without --target)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Made again by the program or by builds, or too large to be worth copying every week.
SKIP_FOLDERS = ("tts_audio", "voice_tmp", "tmp_votes", "cache", "__pycache__", "theme_previews",
                ".pytest_cache", ".trash", ".obsidian\\cache")
LOG_NAME = "backup_log.txt"
STAMP_NAME = "LAST_BACKUP.txt"


@dataclass(frozen=True)
class CopyJob:
    name: str
    source: Path
    target: Path
    files: tuple[str, ...] = ()  # empty: the whole folder with its subfolders
    skip: tuple[str, ...] = field(default=SKIP_FOLDERS)


def vault_path() -> Path:
    configured = os.environ.get("CONSENSUS_SECOND_BRAIN")
    if configured:
        return Path(configured)
    from core.paths import on_portable_drive

    return on_portable_drive("Obsidian", "CONSENSUS_SYSTEM")


def backup_jobs(target: Path, *, root: Path = ROOT, vault: Path | None = None) -> list[CopyJob]:
    code = target / "CONSENSUS_SYSTEM"
    jobs = [
        CopyJob("settings (.env)", root, code, files=(".env",)),
        CopyJob("vote records and AURELIUS data (_ARBITER)", root / "_ARBITER", code / "_ARBITER"),
        CopyJob("reports", root / "reports", code / "reports"),
        CopyJob("logs", root / "logs", code / "logs"),
        CopyJob("voice models", root / "voice" / "model", code / "voice" / "model"),
        CopyJob("voice models", root / "voice" / "models", code / "voice" / "models"),
        CopyJob("GLaDOS voice models", root / "external" / "glados-tts" / "glados-tts-main" / "models",
                code / "external" / "glados-tts" / "glados-tts-main" / "models"),
    ]
    vault = vault if vault is not None else vault_path()
    jobs.append(CopyJob("Obsidian vault", vault, target / "Obsidian" / vault.name))
    return jobs


def robocopy_command(job: CopyJob, log: Path) -> list[str]:
    command = ["robocopy", str(job.source), str(job.target), *job.files]
    if not job.files:
        command.append("/E")  # with subfolders; no /MIR, so nothing on the backup is ever deleted
    if job.skip and not job.files:
        command += ["/XD", *job.skip]
    return command + ["/R:1", "/W:2", "/FFT", "/NP", "/NDL", "/NFL", f"/UNILOG+:{log}"]


def drive_connected(target: Path) -> bool:
    anchor = Path(target.anchor) if target.anchor else target
    return anchor.exists()


Runner = Callable[[Sequence[str]], int]


def _run_robocopy(command: Sequence[str]) -> int:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(list(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          creationflags=flags).returncode


def run_backup(target: Path, *, jobs: list[CopyJob] | None = None, runner: Runner = _run_robocopy,
               now: Callable[[], dt.datetime] = dt.datetime.now) -> dict:
    if not drive_connected(target):
        return {"status": "skipped", "reason": f"{target.anchor or target} is not connected", "jobs": []}
    target.mkdir(parents=True, exist_ok=True)
    log = target / LOG_NAME
    results = []
    for job in jobs if jobs is not None else backup_jobs(target):
        if not job.source.exists() or (job.files and not all((job.source / f).exists() for f in job.files)):
            results.append({"name": job.name, "status": "missing"})
            continue
        code = runner(robocopy_command(job, log))
        # robocopy: 0-7 means it worked (0 = nothing new); 8 or more means some files could not be copied
        results.append({"name": job.name, "status": "ok" if code < 8 else "some_files_failed", "code": code})
    failed = [r for r in results if r["status"] == "some_files_failed"]
    status = "partial" if failed else "ok"
    from config.version import SYSTEM_VERSION

    lines = [f"Last backup: {now():%Y-%m-%d %H:%M} (CONSENSUS {SYSTEM_VERSION}) - {status}"]
    lines += [f"- {r['name']}: {r['status']}" for r in results]
    if failed:
        lines.append(f"Details of files that could not be copied (often a file in use): {LOG_NAME}")
    (target / STAMP_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": status, "jobs": results}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy the owner's own CONSENSUS data to a backup drive.")
    parser.add_argument("--target", default=os.environ.get("CONSENSUS_BACKUP_DIR", ""),
                        help="Backup folder, for example I:\\Backup\\CONSENSUS_DATA.")
    args = parser.parse_args(argv)
    if not args.target:
        print("BACKUP NOT SET UP: give --target or set CONSENSUS_BACKUP_DIR.", flush=True)
        return 2
    result = run_backup(Path(args.target))
    if result["status"] == "skipped":
        print(f"BACKUP SKIPPED: {result['reason']}; nothing was copied.", flush=True)
        return 0
    for job in result["jobs"]:
        print(f"{job['name']}: {job['status']}", flush=True)
    print(f"BACKUP {result['status'].upper()}: {args.target}", flush=True)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
