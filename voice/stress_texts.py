from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


STRESS_TEST_ROOT = Path(__file__).with_name("stress_tests")
MANIFEST_PATH = STRESS_TEST_ROOT / "manifest.json"


def load_stress_manifest() -> Dict[str, Dict[str, str]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def list_stress_keys(profile: str | None = None) -> List[str]:
    manifest = load_stress_manifest()
    if profile is not None:
        return sorted(manifest.get(profile, {}))
    return sorted(f"{profile_name}:{key}" for profile_name, items in manifest.items() for key in items)


def load_stress_text(profile: str, key: str) -> str:
    manifest = load_stress_manifest()
    try:
        relative_path = manifest[profile][key]
    except KeyError as exc:
        available = ", ".join(list_stress_keys(profile)) or "none"
        raise KeyError(f"Unknown stress test {profile}:{key}. Available: {available}") from exc
    return (STRESS_TEST_ROOT / relative_path).read_text(encoding="utf-8").strip()
