@echo off
setlocal
set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%boot.ps1" %*
exit /b %ERRORLEVEL%
