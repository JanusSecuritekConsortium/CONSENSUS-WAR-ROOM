import json
import re
from pathlib import Path

from core.paths import SYSTEM_ROOT
from voice import voice_check
from voice.voice_profiles import CONFIG_PATH, PATH_KEYS, resolve_voice_path


def test_bundled_voice_config_names_no_drive_letter():
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for name, profile in raw["profiles"].items():
        for key in PATH_KEYS:
            value = profile.get(key) or ""
            assert not re.match(r"^[A-Za-z]:", value), f"{name}.{key} names a drive letter: {value}"


def test_drive_prefix_follows_portable_drive(monkeypatch):
    monkeypatch.setattr("voice.voice_profiles.on_portable_drive", lambda *parts: Path("E:/", *parts))
    assert Path(resolve_voice_path("{drive}/Tools/ffmpeg/bin")) == Path("E:/Tools/ffmpeg/bin")


def test_relative_path_is_inside_checkout_and_absolute_is_kept():
    assert Path(resolve_voice_path("voice/models")) == SYSTEM_ROOT / "voice/models"
    assert resolve_voice_path("C:/elsewhere/python.exe") == "C:/elsewhere/python.exe"


def test_voice_check_reports_missing_files_and_archive_warning(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_check, "SYSTEM_ROOT", tmp_path)
    archived = tmp_path / "archive" / "env" / "python.exe"
    archived.parent.mkdir(parents=True)
    archived.write_text("")
    ffmpeg_dir = tmp_path / "ffmpeg"
    ffmpeg_dir.mkdir()
    (ffmpeg_dir / "ffmpeg.exe").write_text("")
    row = voice_check.check_profile(
        "TEST",
        {
            "rvc_model_path": str(tmp_path / "missing.pth"),
            "rvc_python": str(archived),
            "rvc_ffmpeg_dir": str(ffmpeg_dir),
        },
    )
    assert not row["ok"]
    assert any("voice model missing" in problem for problem in row["problems"])
    assert any("archive folder" in warning for warning in row["warnings"])
    assert row["ffmpeg"] == str(ffmpeg_dir / "ffmpeg.exe")


def test_voice_check_fails_without_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_check.shutil, "which", lambda name: None)
    row = voice_check.check_profile("TEST", {"rvc_ffmpeg_dir": str(tmp_path)})
    assert not row["ok"]
    assert "ffmpeg not found" in row["problems"][0]


def _venv(root: Path, home: Path) -> Path:
    python = root / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"")
    (root / "pyvenv.cfg").write_text(f"home = {home}\nversion = 3.10.9\n", encoding="utf-8")
    return python


def test_voice_check_reports_a_venv_whose_base_python_is_gone(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_check.shutil, "which", lambda name: "ffmpeg")
    python = _venv(tmp_path / "rvc_env", tmp_path / "moved-away")
    row = voice_check.check_profile("TEST", {"rvc_python": str(python), "native_python": str(python)})
    assert not row["ok"]
    assert len([p for p in row["problems"] if p.startswith("base Python missing")]) == 1


def test_voice_check_accepts_a_venv_whose_base_python_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_check.shutil, "which", lambda name: "ffmpeg")
    base = tmp_path / "uv-python"
    base.mkdir()
    python = _venv(tmp_path / "rvc_env", base)
    assert voice_check.check_profile("TEST", {"rvc_python": str(python)})["ok"]
