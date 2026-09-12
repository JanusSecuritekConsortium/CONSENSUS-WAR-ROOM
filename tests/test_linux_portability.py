import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from core.paths import SYSTEM_ROOT
from voice.linux_audio import EspeakBackend, play_wav
from voice.voice_profiles import get_voice_profile, load_voice_config
from voice.tts_backends import create_system_backend, WindowsSAPIBackend


def test_linux_profiles_use_native_paths_and_separate_voice_environment():
    with patch("sys.platform", "linux"):
        for name in ("AURELIUS", "ARBITER_GLADOS"):
            settings = get_voice_profile(name).settings
            assert settings["rvc_python"] == str(SYSTEM_ROOT / ".venv-voice/bin/python")
            assert settings["output_dir"] == str(SYSTEM_ROOT / "_ARBITER/tts_audio")
            assert settings["base_tts"] == "espeak"
            assert "Scripts" not in settings["rvc_python"]


def test_windows_profiles_keep_existing_voice_settings():
    path = SYSTEM_ROOT / "voice/voice_config.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    with patch("sys.platform", "win32"):
        assert load_voice_config(path) == original
        assert isinstance(create_system_backend(), WindowsSAPIBackend)


def test_custom_config_does_not_receive_bundled_overrides(tmp_path):
    path = tmp_path / "custom.json"
    path.write_text(json.dumps({"profiles": {"AURELIUS": {"backend": "custom"}}}))
    with patch("sys.platform", "linux"):
        assert get_voice_profile("AURELIUS", path).backend == "custom"


def test_linux_backend_reports_missing_dependency():
    with patch("sys.platform", "linux"), patch("voice.linux_audio.shutil.which", return_value=None):
        result = create_system_backend().speak("Hello")
    assert not result.ok
    assert not result.metadata["played"]
    assert "espeak" in result.metadata["error"]


def test_speech_text_is_stdin_not_shell_or_command_options():
    text = "--help; $(echo secret) 'quoted'"
    with patch("voice.linux_audio.shutil.which", return_value="/usr/bin/espeak-ng"), patch("voice.linux_audio.subprocess.run") as run:
        result = EspeakBackend().speak(text)
    assert result.ok
    assert run.call_args.kwargs["input"] == text
    assert text not in run.call_args.args[0]
    assert not run.call_args.kwargs.get("shell", False)


def test_failed_player_does_not_report_success(tmp_path):
    wav = tmp_path / "voice.wav"
    wav.write_bytes(b"audio")
    with patch("voice.linux_audio.shutil.which", return_value="/usr/bin/paplay"), patch("voice.linux_audio.subprocess.run", side_effect=subprocess.CalledProcessError(1, "paplay")):
        result = play_wav(wav)
    assert not result.ok
    assert not result.metadata["played"]


def test_wav_synthesis_requires_output(tmp_path):
    with patch("voice.linux_audio.shutil.which", return_value="/usr/bin/espeak-ng"), patch("voice.linux_audio.subprocess.run"):
        result = EspeakBackend().synthesize_to_wav("Hello", tmp_path / "missing.wav")
    assert not result.ok


def test_adapters_use_linux_playback(tmp_path):
    from voice.glados_adapter import GladosAdapter
    from voice.rvc_adapter import RVCAdapter
    from voice.tts_backends import TTSBackendResult
    expected = TTSBackendResult(ok=True, metadata={"played": True})
    with patch("sys.platform", "linux"), patch("voice.linux_audio.play_wav", return_value=expected) as play:
        for cls in (GladosAdapter, RVCAdapter):
            assert cls._play_wav(None, tmp_path / "sample.wav") is expected
    assert play.call_count == 2


def test_linux_validation_does_not_claim_windows_screenshots_passed():
    from tools import boot
    with patch("sys.platform", "linux"), patch.object(boot, "_run_command", return_value=0) as run:
        assert boot.run_release_validation() == 2
    assert run.call_count == 2
    assert all("export_theme_gallery.py" not in str(call) for call in run.call_args_list)
