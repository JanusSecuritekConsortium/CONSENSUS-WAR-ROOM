@echo off
rem Opens the CONSENSUS guest door (docs\GUEST_DOOR.md). Close this window to close the door.
cd /d "%~dp0\..\.."
".venv\Scripts\python.exe" -m integrations.guest.server
pause
