from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from core.paths import SYSTEM_ROOT


ACTIVE_COMPILE_TARGETS = (
    "main.py",
    "consensus_war_room_genesis.py",
    "config",
    "core",
    "integrations",
    "voice",
    "assistant",
    "ui",
    "tests",
    "tools",
)

EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "_ARBITER",
    "__pycache__",
    "archive",
    "cache",
    "external",
    "htmlcov",
    "logs",
    "node_modules",
    "outputs",
    "rvc_env",
    "tts_audio",
    "venv",
}


@dataclass(frozen=True)
class CompileResult:
    compiled: List[Path]
    failures: List[str]
    skipped_directories: List[Path]

    @property
    def ok(self) -> bool:
        return not self.failures


def iter_active_python_sources(root: Path = SYSTEM_ROOT) -> Iterable[Path]:
    for path in _collect_active_sources(root)[0]:
        yield path


def _collect_active_sources(root: Path = SYSTEM_ROOT) -> tuple[List[Path], List[Path]]:
    sources: List[Path] = []
    skipped_directories: List[Path] = []
    for target_name in ACTIVE_COMPILE_TARGETS:
        target = root / target_name
        if not target.exists():
            continue
        if target.is_file():
            if target.suffix == ".py":
                sources.append(target)
            continue
        for current_root, dirs, files in _walk_active_directory(target, root):
            skipped = [current_root / dirname for dirname in dirs if dirname in EXCLUDED_PARTS]
            skipped_directories.extend(skipped)
            dirs[:] = [dirname for dirname in dirs if dirname not in EXCLUDED_PARTS]
            for filename in files:
                path = current_root / filename
                if path.suffix == ".py":
                    sources.append(path)
    return sorted(set(sources)), sorted(set(skipped_directories))


def _walk_active_directory(target: Path, root: Path):
    import os

    for current, dirs, files in os.walk(target):
        current_root = Path(current)
        relative_parts = set(current_root.relative_to(root).parts)
        if relative_parts & EXCLUDED_PARTS:
            dirs[:] = []
            continue
        yield current_root, dirs, files


def compile_active_sources(root: Path = SYSTEM_ROOT) -> CompileResult:
    sources, skipped_directories = _collect_active_sources(root)
    compiled: List[Path] = []
    failures: List[str] = []
    for path in sources:
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            compiled.append(path)
        except Exception as exc:
            failures.append(f"{path}: {exc}")
    return CompileResult(compiled=compiled, failures=failures, skipped_directories=skipped_directories)


def print_compile_report(result: CompileResult, root: Path = SYSTEM_ROOT) -> None:
    if result.ok:
        print(f"ACTIVE COMPILE PASS: {len(result.compiled)} files")
    else:
        print(f"ACTIVE COMPILE FAIL: {len(result.failures)} failures")
        for failure in result.failures:
            print(f"[FAIL] {failure}")
    print(f"Compiled file count: {len(result.compiled)}")
    print(f"Skipped directory count: {len(result.skipped_directories)}")
    if result.failures:
        print("Failed files:")
        for failure in result.failures:
            print(f"- {failure}")
    print("Compiled roots:")
    for target in ACTIVE_COMPILE_TARGETS:
        print(f"- {target}")
    print("Excluded roots:")
    for target in sorted(EXCLUDED_PARTS):
        print(f"- {target}")
