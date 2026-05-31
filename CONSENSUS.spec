# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH)
hiddenimports = sorted(set(collect_submodules("flet") + collect_submodules("flet_desktop")))
datas = [
    (str(ROOT / "static"), "static"),
    (str(ROOT / "_ARBITER" / "genesis_config.json"), "_ARBITER"),
    (str(ROOT / "voice" / "voice_config.json"), "voice"),
]

a = Analysis(
    ["consensus_launcher.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CONSENSUS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "static" / "icons" / "consensus_icon.ico"),
    version=str(ROOT / "packaging" / "windows_version_info.txt"),
)
