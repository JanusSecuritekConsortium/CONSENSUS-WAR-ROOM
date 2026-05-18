from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from core.paths import SYSTEM_ROOT


ACTIVE_COMPILE_TARGETS = (
    "main.py",
    "consensus_war_room_genesis.py",
    "core",
    "config",
    "integrations",
    "ui",
    "assistant",
    "voice",
    "monoliths",
    "tests",
    "scripts",
)

EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "archive",
    "_ARBITER",
}


@dataclass(frozen=True)
class CompileResult:
    compiled: List[Path]
    failures: List[str]

    @property
    def ok(self) -> bool:
        return not self.failures


def iter_active_python_sources(root: Path = SYSTEM_ROOT) -> Iterable[Path]:
    for target_name in ACTIVE_COMPILE_TARGETS:
        target = root / target_name
        if not target.exists():
            continue
        if target.is_file():
            if target.suffix == ".py":
                yield target
            continue
        for path in target.rglob("*.py"):
            relative_parts = set(path.relative_to(root).parts)
            if relative_parts & EXCLUDED_PARTS:
                continue
            yield path


def compile_active_sources(root: Path = SYSTEM_ROOT) -> CompileResult:
    compiled: List[Path] = []
    failures: List[str] = []
    for path in sorted(set(iter_active_python_sources(root))):
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            compiled.append(path)
        except Exception as exc:
            failures.append(f"{path}: {exc}")
    return CompileResult(compiled=compiled, failures=failures)


def print_compile_report(result: CompileResult, root: Path = SYSTEM_ROOT) -> None:
    if result.ok:
        print(f"ACTIVE COMPILE PASS: {len(result.compiled)} files")
    else:
        print(f"ACTIVE COMPILE FAIL: {len(result.failures)} failures")
        for failure in result.failures:
            print(f"[FAIL] {failure}")
    print("Compiled roots:")
    for target in ACTIVE_COMPILE_TARGETS:
        print(f"- {target}")
    print("Excluded roots:")
    for target in sorted(EXCLUDED_PARTS):
        print(f"- {target}")
