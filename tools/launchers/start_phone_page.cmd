@echo off
rem Opens the CONSENSUS phone page on this PC's Tailscale address (docs\PHONE_ACCESS.md).
rem Close this window to close the page.
cd /d "%~dp0\..\.."
".venv\Scripts\python.exe" -m integrations.phone.server --host tailscale
pause
