@echo off
rem Add, change or remove CONSENSUS operator profiles and their PINs (docs\OPERATOR_LOCK.md).
rem CONSENSUS.exe in dist and the tools run from source share one profile file (_ARBITER\users.json).
cd /d "%~dp0\..\.."
if exist "dist\CONSENSUS.exe" (
    "dist\CONSENSUS.exe" --users
) else (
    ".venv\Scripts\python.exe" -m tools.users
)
pause
