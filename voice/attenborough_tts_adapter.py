from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

from core.paths import ARBITER_DIR


@dataclass
class TTSRenderResult:
    ok: bool
    audio_path: Optional[str] = None
    mode: str = "dry_run"
    metadata: Dict[str, object] = field(default_factory=dict)


class AttenboroughTTSAdapter:
    """Calm documentary-style TTS adapter; it does not clone a living person's voice."""

    def __init__(
        self,
        script_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        manifest_factory: Optional[Callable[[], Path]] = None,
    ) -> None:
        self.script_path = script_path
        self.output_dir = output_dir or ARBITER_DIR / "aurelius"
        self.manifest_factory = manifest_factory

    def synthesize(self, text: str) -> TTSRenderResult:
        cleaned = text.strip()
        if not cleaned:
            return TTSRenderResult(ok=False, mode="empty", metadata={"error": "empty_text"})
        if self.script_path and self.script_path.exists():
            return self._synthesize_with_script(cleaned)
        pyttsx3_result = self._synthesize_with_pyttsx3(cleaned)
        if pyttsx3_result.ok:
            return pyttsx3_result
        return self._write_manifest(cleaned, pyttsx3_result.metadata)

    def _synthesize_with_script(self, text: str) -> TTSRenderResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / "aurelius_tts.wav"
        try:
            completed = subprocess.run(
                [sys.executable, str(self.script_path), "--text", text, "--output", str(target)],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception as exc:
            return TTSRenderResult(ok=False, mode="script", metadata={"error": str(exc)})
        return TTSRenderResult(
            ok=completed.returncode == 0 and target.exists(),
            audio_path=str(target) if target.exists() else None,
            mode="script",
            metadata={"returncode": completed.returncode, "stderr": completed.stderr[-500:]},
        )

    def _synthesize_with_pyttsx3(self, text: str) -> TTSRenderResult:
        try:
            import pyttsx3  # type: ignore
        except Exception as exc:
            return TTSRenderResult(ok=False, mode="pyttsx3", metadata={"error": str(exc)})
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / "aurelius_tts.wav"
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 142)
            engine.save_to_file(text, str(target))
            engine.runAndWait()
        except Exception as exc:
            return TTSRenderResult(ok=False, mode="pyttsx3", metadata={"error": str(exc)})
        return TTSRenderResult(ok=target.exists(), audio_path=str(target) if target.exists() else None, mode="pyttsx3")

    def _write_manifest(self, text: str, fallback_metadata: Dict[str, object]) -> TTSRenderResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.manifest_factory() if self.manifest_factory else self.output_dir / "aurelius_tts_manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": "dry_run",
            "voice_policy": "documentary pacing; no living-person voice cloning",
            "text": text,
            "fallback_metadata": fallback_metadata,
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return TTSRenderResult(ok=True, audio_path=str(target), mode="dry_run", metadata={"manifest": str(target)})
