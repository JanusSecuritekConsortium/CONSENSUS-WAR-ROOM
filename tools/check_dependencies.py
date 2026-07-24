from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION


REQUIRED_DEPENDENCIES = (
    "psutil",
    "flet",
    "flet_desktop",
    "requests",
    "fastapi",
    "uvicorn",
    "pydantic",
    "websockets",
)
OPTIONAL_DEPENDENCIES = ("GPUtil",)
INSTALL_HINTS = [
    "python -m pip install -e .",
    "python -m pip install psutil",
]


def _module_status(module_name: str) -> Dict[str, Any]:
    spec = importlib.util.find_spec(module_name)
    return {
        "name": module_name,
        "available": spec is not None,
        "kind": "python_module",
        "origin": str(spec.origin) if spec is not None and spec.origin else None,
    }


def build_dependency_report() -> Dict[str, Any]:
    required = {name: _module_status(name) for name in REQUIRED_DEPENDENCIES}
    optional = {name: _module_status(name) for name in OPTIONAL_DEPENDENCIES}
    nvidia_smi = shutil.which("nvidia-smi")
    optional["nvidia-smi"] = {
        "name": "nvidia-smi",
        "available": nvidia_smi is not None,
        "kind": "executable",
        "path": nvidia_smi,
    }
    missing_required = [name for name, status in required.items() if not status["available"]]
    missing_optional = [name for name, status in optional.items() if not status["available"]]
    return {
        "version": SYSTEM_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "READY" if not missing_required else "ERROR",
        "required_dependencies": required,
        "optional_dependencies": optional,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "install_hints": INSTALL_HINTS if missing_required else [],
    }


def print_human_report(report: Dict[str, Any]) -> None:
    print(f"CONSENSUS dependency status: {report['status']}")
    print("Required:")
    for name, status in report["required_dependencies"].items():
        label = "OK" if status["available"] else "MISSING"
        print(f"  {name}: {label}")
    print("Optional:")
    for name, status in report["optional_dependencies"].items():
        label = "OK" if status["available"] else "UNAVAILABLE"
        print(f"  {name}: {label}")
    if report["missing_required"]:
        print("Install hints:")
        for hint in report["install_hints"]:
            print(f"  {hint}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CONSENSUS runtime and optional telemetry dependencies.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    args = parser.parse_args()
    report = build_dependency_report()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print_human_report(report)
    return 0 if not report["missing_required"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
