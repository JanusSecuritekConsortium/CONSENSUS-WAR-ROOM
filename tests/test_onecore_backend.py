"""Aurelius renders its base voice with a OneCore voice (Mark) and falls back to SAPI when that fails."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice import tts_backends
from voice.tts_backends import TTSBackendResult, WindowsOneCoreBackend, WindowsSAPIBackend, create_system_backend


@unittest.skipIf(sys.platform.startswith("linux"), "Windows voices only")
class OneCoreBackendTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.target = Path(folder.name) / "base.wav"
        self.backend = WindowsOneCoreBackend(rate=145, voice_names=["Microsoft Mark", "Microsoft David"])
        self.calls = []

    def fake_run(self, writes, stdout="Microsoft Mark|en-US|Male", returncode=0):
        def run(command, **kwargs):
            environment = kwargs["env"]
            self.calls.append({key: value for key, value in environment.items() if key.startswith("ONECORE_")})
            self.calls[-1]["text"] = Path(environment["ONECORE_TEXT"]).read_text(encoding="utf-8")
            if writes:
                Path(environment["ONECORE_OUT"]).write_bytes(b"RIFF")
            return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="" if returncode == 0 else "boom")
        return run

    def test_renders_with_the_first_requested_voice(self):
        with mock.patch.object(tts_backends.subprocess, "run", self.fake_run(writes=True)):
            result = self.backend.synthesize_to_wav("It's done, Commander.", self.target)
        self.assertTrue(result.ok)
        self.assertEqual(result.mode, "windows_onecore")
        self.assertEqual(result.metadata["voice"], {"name": "Microsoft Mark", "language": "en-US", "gender": "Male"})
        self.assertEqual(self.calls[0]["ONECORE_VOICES"], "Microsoft Mark|Microsoft David")
        self.assertEqual(self.calls[0]["ONECORE_RATE"], "1.0")
        self.assertEqual(self.calls[0]["text"], "It's done, Commander.")  # passed by file, so quotes survive
        self.assertEqual(list(self.target.parent.glob("*.txt")), [])

    def test_falls_back_to_sapi_when_onecore_fails(self):
        sapi = TTSBackendResult(ok=True, mode="windows_sapi", audio_path=str(self.target), metadata={})
        with mock.patch.object(tts_backends.subprocess, "run", self.fake_run(writes=False, returncode=1)), \
                mock.patch.object(WindowsSAPIBackend, "synthesize_to_wav", return_value=sapi) as fallback:
            result = self.backend.synthesize_to_wav("Hello.", self.target)
        fallback.assert_called_once()
        self.assertEqual(result.mode, "windows_sapi")
        self.assertEqual(result.metadata["onecore_error"], "boom")

    def test_engine_choice(self):
        self.assertIsInstance(create_system_backend(engine="windows_onecore"), WindowsOneCoreBackend)
        self.assertNotIsInstance(create_system_backend(), WindowsOneCoreBackend)


if __name__ == "__main__":
    unittest.main()
