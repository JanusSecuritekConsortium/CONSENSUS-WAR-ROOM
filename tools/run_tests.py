from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODEL_CACHE_PATH = ROOT / "_ARBITER" / "provider_model_cache.json"

CATEGORIES = ("FAST", "GUI", "SLOW", "PROVIDER", "INTEGRATION")
GUI_HEAVY_PATTERNS = ("gui_", "theme_logo", "theme_header", "compact_logo")
PROVIDER_PATTERNS = ("provider", "msty", "ollama", "backend", "model_cache", "health_uses_model")
INTEGRATION_PATTERNS = ("runtime", "bundle", "snapshot", "manifest", "integrity", "cli", "submission", "lifecycle")
SLOW_NAME_PATTERNS = ("gui_window", "gui_header", "theme_logo", "msty_runtime", "provider_cli")
GUI_EXPENSIVE_SETUP_TOKENS = (
    "create_gui_state(",
    "ft.app(",
    "gui_smoke_check",
    "capture_gui_snapshot",
    "export_theme_gallery",
)


def default_report_path() -> Path:
    from config.version import SYSTEM_VERSION

    return ROOT / "reports" / f"verification_v{SYSTEM_VERSION}.json"


def discover_tests(root: Path = ROOT) -> list[Path]:
    return sorted((root / "tests").glob("test_*.py"))


def categorize_test(path: Path) -> set[str]:
    name = path.name.lower()
    categories: set[str] = set()
    if "fast_path" in name:
        return {"FAST"}
    if any(pattern in name for pattern in GUI_HEAVY_PATTERNS):
        categories.add("GUI")
    if any(pattern in name for pattern in PROVIDER_PATTERNS):
        categories.add("PROVIDER")
    if any(pattern in name for pattern in INTEGRATION_PATTERNS):
        categories.add("INTEGRATION")
    if any(pattern in name for pattern in SLOW_NAME_PATTERNS):
        categories.add("SLOW")
    if not categories or categories == {"INTEGRATION"}:
        categories.add("FAST")
    return categories


def test_metadata(path: Path) -> dict[str, Any]:
    categories = sorted(categorize_test(path))
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        source = ""
    return {
        "file": str(path.relative_to(ROOT)),
        "categories": categories,
        "gui_launch_heavy": "GUI" in categories and any(token in source for token in GUI_EXPENSIVE_SETUP_TOKENS),
    }


def select_tests(tests: list[Path], selected_categories: set[str] | None) -> list[Path]:
    if not selected_categories:
        return tests
    return [path for path in tests if categorize_test(path) & selected_categories]


def run_test_file(path: Path, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        MODEL_CACHE_PATH.unlink()
    except FileNotFoundError:
        pass
    env = os.environ.copy()
    pythonpath = str(ROOT)
    if env.get("PYTHONPATH"):
        pythonpath = pythonpath + os.pathsep + env["PYTHONPATH"]
    env["PYTHONPATH"] = pythonpath
    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        status = "pass" if completed.returncode == 0 else "fail"
        return {
            **test_metadata(path),
            "status": status,
            "returncode": completed.returncode,
            "duration_seconds": round(time.perf_counter() - started, 4),
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            **test_metadata(path),
            "status": "fail",
            "returncode": None,
            "duration_seconds": round(time.perf_counter() - started, 4),
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {timeout} seconds",
        }


def build_duration_report(results: list[dict[str, Any]], slow_threshold_seconds: float, total_budget_seconds: float) -> dict[str, Any]:
    slowest = sorted(results, key=lambda item: float(item.get("duration_seconds", 0)), reverse=True)[:10]
    total_duration = round(sum(float(item.get("duration_seconds", 0)) for item in results), 4)
    slow_tests = [
        {"file": item["file"], "duration_seconds": item["duration_seconds"]}
        for item in results
        if float(item.get("duration_seconds", 0)) > slow_threshold_seconds
    ]
    gui_launch_heavy = [
        {"file": item["file"], "duration_seconds": item.get("duration_seconds"), "categories": item.get("categories", [])}
        for item in results
        if item.get("gui_launch_heavy")
    ]
    warnings: list[str] = []
    for item in slow_tests:
        warnings.append(f"slow_test: {item['file']} exceeded {slow_threshold_seconds:g}s ({item['duration_seconds']}s)")
    if total_duration > total_budget_seconds:
        warnings.append(f"total_budget: suite exceeded {total_budget_seconds:g}s ({total_duration}s)")
    return {
        "total_duration_seconds": total_duration,
        "slow_threshold_seconds": slow_threshold_seconds,
        "total_budget_seconds": total_budget_seconds,
        "slowest_10": [
            {"file": item["file"], "duration_seconds": item["duration_seconds"], "categories": item.get("categories", [])}
            for item in slowest
        ],
        "slow_tests": slow_tests,
        "gui_launch_heavy_tests": gui_launch_heavy,
        "warnings": warnings,
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _previous_duration_manifest(report_path: Path) -> tuple[Path, dict[str, Any]] | None:
    from config.version import SYSTEM_VERSION

    candidates: list[Path] = []
    if report_path.exists():
        candidates.append(report_path)
    if report_path.parent.exists():
        candidates.extend(
            path
            for path in report_path.parent.glob("verification_v*.json")
            if path.is_file() and path not in candidates
        )
    valid: list[tuple[Path, dict[str, Any]]] = []
    for path in candidates:
        manifest = _read_json(path)
        if not manifest:
            continue
        if isinstance(manifest.get("duration_report"), dict) and isinstance(manifest.get("tests"), list):
            valid.append((path, manifest))
    if not valid:
        return None
    previous_version = [
        (path, manifest)
        for path, manifest in valid
        if str(manifest.get("version")) != SYSTEM_VERSION
    ]
    choices = previous_version or valid
    return max(choices, key=lambda item: item[0].stat().st_mtime)


def build_duration_comparison(results: list[dict[str, Any]], report_path: Path) -> dict[str, Any] | None:
    previous = _previous_duration_manifest(report_path)
    if previous is None:
        return None
    previous_path, previous_manifest = previous
    previous_tests = {
        str(item.get("file")): float(item.get("duration_seconds", 0))
        for item in previous_manifest.get("tests", [])
        if isinstance(item, dict) and item.get("file")
    }
    compared: list[dict[str, Any]] = []
    for item in results:
        file_name = str(item.get("file"))
        if file_name not in previous_tests:
            continue
        current_duration = float(item.get("duration_seconds", 0))
        previous_duration = previous_tests[file_name]
        compared.append(
            {
                "file": file_name,
                "previous_seconds": round(previous_duration, 4),
                "current_seconds": round(current_duration, 4),
                "delta_seconds": round(current_duration - previous_duration, 4),
            }
        )
    if not compared:
        return None
    current_total = round(sum(float(item.get("duration_seconds", 0)) for item in results), 4)
    previous_total = float(
        previous_manifest.get("duration_report", {}).get(
            "total_duration_seconds",
            previous_manifest.get("duration_seconds", 0),
        )
    )
    return {
        "baseline_manifest": str(previous_path),
        "baseline_version": previous_manifest.get("version"),
        "current_total_seconds": current_total,
        "baseline_total_seconds": round(previous_total, 4),
        "delta_total_seconds": round(current_total - previous_total, 4),
        "tests_compared": len(compared),
        "improved_10": sorted(compared, key=lambda item: item["delta_seconds"])[:10],
        "regressed_10": sorted(compared, key=lambda item: item["delta_seconds"], reverse=True)[:10],
    }


def write_manifest(
    results: list[dict[str, Any]],
    report_path: Path,
    selected_categories: list[str],
    duration_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from config.version import SYSTEM_VERSION

    passed = sum(1 for item in results if item["status"] == "pass")
    failed = len(results) - passed
    duration = duration_report or build_duration_report(results, 30.0, 900.0)
    duration_comparison = build_duration_comparison(results, report_path)
    manifest = {
        "version": SYSTEM_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_executable": sys.executable,
        "selected_categories": selected_categories,
        "screenshot_status": "MANUAL_REVIEW_REQUIRED",
        "screenshot_note": "Automated screenshot export is not a release gate for this pass; user-provided manual screenshots drive visual review.",
        "test_files_run": len(results),
        "passed": passed,
        "failed": failed,
        "duration_seconds": duration["total_duration_seconds"],
        "duration_report": duration,
        "duration_comparison": duration_comparison,
        "gui_launch_heavy_tests": duration["gui_launch_heavy_tests"],
        "tests": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _selected_categories_from_args(args: argparse.Namespace) -> set[str]:
    selected = set()
    for flag, category in (
        ("fast", "FAST"),
        ("gui", "GUI"),
        ("slow", "SLOW"),
        ("provider", "PROVIDER"),
        ("integration", "INTEGRATION"),
    ):
        if getattr(args, flag):
            selected.add(category)
    return set() if args.all or not selected else selected


def _print_list(tests: list[Path], json_output: bool) -> None:
    entries = [test_metadata(path) for path in tests]
    if json_output:
        print(json.dumps({"tests": entries}, indent=2), flush=True)
        return
    for entry in entries:
        print(f"{entry['file']} [{', '.join(entry['categories'])}]", flush=True)


def _print_duration_summary(duration_report: dict[str, Any], json_output: bool) -> None:
    if json_output:
        return
    print("SLOWEST TESTS", flush=True)
    for item in duration_report["slowest_10"]:
        print(f"- {item['file']} {item['duration_seconds']}s [{', '.join(item.get('categories', []))}]", flush=True)
    for warning in duration_report["warnings"]:
        print(f"WARN {warning}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CONSENSUS script-style tests without requiring pytest.")
    parser.add_argument("--timeout", type=float, default=180.0, help="Per-test timeout in seconds.")
    parser.add_argument("--report", type=Path, default=default_report_path(), help="Verification manifest path.")
    parser.add_argument("--fast", action="store_true", help="Run FAST tests.")
    parser.add_argument("--gui", action="store_true", help="Run GUI tests.")
    parser.add_argument("--slow", action="store_true", help="Run SLOW tests.")
    parser.add_argument("--provider", action="store_true", help="Run PROVIDER tests.")
    parser.add_argument("--integration", action="store_true", help="Run INTEGRATION tests.")
    parser.add_argument("--all", action="store_true", help="Run the full suite.")
    parser.add_argument("--list", action="store_true", help="List selected tests without running them.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON summary.")
    parser.add_argument("--slow-threshold", type=float, default=30.0, help="Warn when one test exceeds this many seconds.")
    parser.add_argument("--total-budget", type=float, default=900.0, help="Warn when selected suite exceeds this many seconds.")
    parser.add_argument("--strict-budget", action="store_true", help="Fail when duration budget warnings are present.")
    args = parser.parse_args()

    selected_categories = _selected_categories_from_args(args)
    tests = select_tests(discover_tests(), selected_categories)
    if args.list:
        _print_list(tests, args.json)
        return 0
    if not tests:
        print("FAIL no tests/test_*.py files discovered for selected categories", flush=True)
        write_manifest([], args.report, sorted(selected_categories))
        return 1

    results: list[dict[str, Any]] = []
    for test_path in tests:
        result = run_test_file(test_path, args.timeout)
        results.append(result)
        if not args.json:
            label = "PASS" if result["status"] == "pass" else "FAIL"
            print(f"{label} {result['file']} ({result['duration_seconds']}s)", flush=True)
            if result["status"] != "pass":
                stderr = str(result.get("stderr") or "").strip()
                stdout = str(result.get("stdout") or "").strip()
                if stderr:
                    print(stderr, flush=True)
                elif stdout:
                    print(stdout, flush=True)

    duration_report = build_duration_report(results, args.slow_threshold, args.total_budget)
    manifest = write_manifest(results, args.report, sorted(selected_categories) if selected_categories else ["ALL"], duration_report)
    _print_duration_summary(duration_report, args.json)

    failed_for_budget = args.strict_budget and bool(duration_report["warnings"])
    exit_code = 0 if manifest["failed"] == 0 and not failed_for_budget else 1
    if args.json:
        print(json.dumps({"summary": manifest, "exit_code": exit_code}, indent=2), flush=True)
    else:
        print(
            "SUMMARY "
            f"pass={manifest['passed']} fail={manifest['failed']} "
            f"total={manifest['test_files_run']} report={args.report}",
            flush=True,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
