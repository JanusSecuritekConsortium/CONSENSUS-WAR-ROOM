@echo off
rem Add, change or remove CONSENSUS operator profiles and their PINs (docs\OPERATOR_LOCK.md).
rem The packaged app keeps its own profiles next to CONSENSUS.exe, so manage them through it when it exists.
cd /d "%~dp0\..\.."
if exist "dist\CONSENSUS.exe" (
    "dist\CONSENSUS.exe" --users
) else (
    ".venv\Scripts\python.exe" -m tools.users
)
pause
