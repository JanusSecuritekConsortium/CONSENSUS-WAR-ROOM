@echo off
setlocal
rem One-time setup for CONSENSUS. Double-click this file, or run it from a terminal.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
