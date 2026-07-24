from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.audio_quality import analyze_wav
from voice.glados_adapter import GladosAdapter
from voice.glados_native import inspect_native_glados_assets
from voice.tts_backends import sapi_voice_status
from voice.voice_profiles import get_voice_profile


def build_preflight(*, verify_hashes: bool = False, render_native: bool = False) -> Dict[str, Any]:
    aurelius = get_voice_profile("AURELIUS")
    glados = get_voice_profile("ARBITER_GLADOS")
    native = inspect_native_glados_assets(verify_hashes=verify_hashes)
    payload: Dict[str, Any] = {
        "native_glados": native,
        "sapi": sapi_voice_status(),
        "profiles": {
            "AURELIUS": _profile_status(aurelius),
            "ARBITER_GLADOS": _profile_status(glados),
        },
    }
    configured = native["ready"] and all(item["configured"] for item in payload["profiles"].values())
    payload["configured"] = configured
    payload["operational"] = configured and payload["sapi"]["ready"]
    if render_native:
        result = GladosAdapter(backend="glados_tts", timeout=600).save_only("Consensus reached. Proposal approved.")
        payload["native_render"] = {
            "ok": result.ok,
            "mode": result.mode,
            "audio_path": result.audio_path,
            "metadata": result.metadata,
        }
        if result.ok and result.audio_path:
            payload["native_render"]["quality"] = analyze_wav(result.audio_path).as_dict()
    return payload


def _profile_status(profile: Any) -> Dict[str, Any]:
    settings = profile.settings
    model = Path(str(settings.get("rvc_model_path", "")))
    staged = Path(str(settings.get("rvc_workdir", ""))) / "assets" / "weights" / str(settings.get("rvc_model_name", ""))
    index = Path(str(settings.get("rvc_index_path", "")))
    source_hash = _sha256(model) if model.is_file() else None
    staged_hash = _sha256(staged) if staged.is_file() else None
    configured = model.is_file() and staged.is_file() and index.is_file() and source_hash == staged_hash
    return {
        "backend": profile.backend,
        "fallback": profile.fallback,
        "model": str(model),
        "model_exists": model.is_file(),
        "staged_model": str(staged),
        "staged_model_exists": staged.is_file(),
        "model_copy_matches": source_hash is not None and source_hash == staged_hash,
        "index": str(index),
        "index_exists": index.is_file(),
        "configured": configured,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GLaDOS and AURELIUS voice assets and backends")
    parser.add_argument("--verify-hashes", action="store_true", help="verify native GLaDOS SHA-256 hashes")
    parser.add_argument("--render-native", action="store_true", help="render and analyze a native GLaDOS smoke-test WAV")
    parser.add_argument("--require-sapi", action="store_true", help="fail when the current session cannot enumerate SAPI voices")
    args = parser.parse_args()
    result = build_preflight(verify_hashes=args.verify_hashes, render_native=args.render_native)
    print(json.dumps(result, indent=2))
    ready = bool(result["configured"])
    if args.require_sapi:
        ready = ready and bool(result["operational"])
    if args.render_native:
        ready = ready and bool(result.get("native_render", {}).get("ok"))
        ready = ready and bool(result.get("native_render", {}).get("quality", {}).get("baseline_ok"))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
