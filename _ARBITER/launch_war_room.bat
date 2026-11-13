@echo off
rem Opens the CONSENSUS War Room. (This file used to start the retired 2025 text console.)
cd /d "%~dp0\.."
if exist "dist\CONSENSUS.exe" (
    start "" "dist\CONSENSUS.exe"
) else (
    ".venv\Scripts\python.exe" consensus_launcher.py
)
