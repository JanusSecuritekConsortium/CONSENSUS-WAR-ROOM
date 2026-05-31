from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "CONSENSUS.spec"
OUTPUT_PATH = ROOT / "dist" / "CONSENSUS.exe"


def build_executable() -> Path:
    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError(
            "PyInstaller is not installed. Run: "
            r".\.venv\Scripts\python.exe -m pip install pyinstaller"
        )
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(SPEC_PATH)],
        cwd=ROOT,
        check=True,
    )
    if not OUTPUT_PATH.exists() or OUTPUT_PATH.stat().st_size == 0:
        raise RuntimeError(f"Executable build did not produce {OUTPUT_PATH}")
    return OUTPUT_PATH


def main() -> int:
    try:
        target = build_executable()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"CONSENSUS executable build failed: {exc}", file=sys.stderr)
        return 1
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
