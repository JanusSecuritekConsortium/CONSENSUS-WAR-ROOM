from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class VoiceInputResult:
    ok: bool
    text: str = ""
    source: str = "none"
    metadata: Dict[str, object] = field(default_factory=dict)


class RikoVoiceAdapter:
    def __init__(
        self,
        latest_input_path: Path | str = "J:/CONSENSUS_SYSTEM/_ARBITER/voice_tmp/latest_input.wav",
        asr_endpoint: str = "http://127.0.0.1:7865/asr",
        timeout: float = 5.0,
    ) -> None:
        self.latest_input_path = Path(latest_input_path)
        self.asr_endpoint = asr_endpoint
        self.timeout = timeout

    def listen_once(self) -> VoiceInputResult:
        if self.latest_input_path.exists():
            return self._transcribe_file(self.latest_input_path)
        return self._transcribe_endpoint()

    def _transcribe_file(self, path: Path) -> VoiceInputResult:
        try:
            import requests  # type: ignore
        except Exception:
            return VoiceInputResult(
                ok=False,
                source=str(path),
                metadata={"error": "requests_unavailable", "audio_path": str(path)},
            )
        try:
            with path.open("rb") as handle:
                response = requests.post(self.asr_endpoint, files={"file": handle}, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return VoiceInputResult(ok=False, source=str(path), metadata={"error": str(exc), "audio_path": str(path)})
        return VoiceInputResult(ok=True, text=str(payload.get("text", "")).strip(), source=str(path), metadata=payload)

    def _transcribe_endpoint(self) -> VoiceInputResult:
        try:
            import requests  # type: ignore
        except Exception:
            return VoiceInputResult(ok=False, source=self.asr_endpoint, metadata={"error": "requests_unavailable"})
        try:
            response = requests.get(self.asr_endpoint, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return VoiceInputResult(ok=False, source=self.asr_endpoint, metadata={"error": str(exc)})
        return VoiceInputResult(ok=True, text=str(payload.get("text", "")).strip(), source=self.asr_endpoint, metadata=payload)
