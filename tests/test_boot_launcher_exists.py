from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_boot_launchers_exist_and_delegate_to_operator_boot() -> None:
    batch = (ROOT / "boot.bat").read_text(encoding="utf-8")
    powershell = (ROOT / "boot.ps1").read_text(encoding="utf-8")
    assert "boot.ps1" in batch
    assert "tools\\boot.py" in powershell
    assert "--safe" in powershell


if __name__ == "__main__":
    test_boot_launchers_exist_and_delegate_to_operator_boot()
    print("test_boot_launcher_exists PASS")
