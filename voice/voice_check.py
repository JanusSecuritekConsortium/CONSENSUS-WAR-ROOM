"""Check that each voice profile's files are present on this machine.

Run with ``python -m voice.voice_check``. It reads files only: it makes no sound and sends nothing.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import SYSTEM_ROOT
from voice.voice_profiles import load_voice_config

# A setting that points into an archive folder works, but a clean-up can remove it without warning.
ARCHIVE_FOLDER = "archive"

FILE_KEYS = {
    "rvc_model_path": "voice model",
    "rvc_index_path": "voice index",
    "rvc_python": "voice conversion Python",
    "native_python": "GLaDOS Python",
}
FOLDER_KEYS = {
    "rvc_workdir": "voice conversion folder",
    "output_dir": "voice note folder",
}


def _inside_archive(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(SYSTEM_ROOT.resolve())
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0].lower() == ARCHIVE_FOLDER


def _find_ffmpeg(settings: Dict[str, Any]) -> Optional[str]:
    folder = settings.get("rvc_ffmpeg_dir")
    if folder:
        for name in ("ffmpeg.exe", "ffmpeg"):
            candidate = Path(str(folder)) / name
            if candidate.is_file():
                return str(candidate)
    return shutil.which("ffmpeg")


def check_profile(name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    problems: List[str] = []
    warnings: List[str] = []
    for key, label in {**FILE_KEYS, **FOLDER_KEYS}.items():
        value = settings.get(key)
        if not value:
            continue
        path = Path(str(value))
        exists = path.is_dir() if key in FOLDER_KEYS else path.is_file()
        if not exists:
            problems.append(f"{label} missing: {path}")
        elif _inside_archive(path):
            warnings.append(f"{label} is inside the archive folder: {path}")
    if settings.get("rvc_workdir"):
        script = Path(str(settings["rvc_workdir"])) / "tools" / "infer_cli.py"
        if not script.is_file():
            problems.append(f"voice conversion script missing: {script}")
    ffmpeg = _find_ffmpeg(settings)
    if ffmpeg is None:
        problems.append("ffmpeg not found in rvc_ffmpeg_dir or on PATH")
    return {"profile": name, "ok": not problems, "ffmpeg": ffmpeg, "problems": problems, "warnings": warnings}


def check(config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    config = config if config is not None else load_voice_config()
    return [check_profile(name, settings) for name, settings in config.get("profiles", {}).items()]


def render(rows: List[Dict[str, Any]]) -> str:
    lines = []
    for row in rows:
        lines.append(f"{row['profile']}: {'ready' if row['ok'] else 'NOT READY'}")
        lines.extend(f"  - {problem}" for problem in row["problems"])
        lines.extend(f"  ! {warning}" for warning in row["warnings"])
    return "\n".join(lines)


def main() -> int:
    rows = check()
    print(render(rows))
    return 0 if all(row["ok"] for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
