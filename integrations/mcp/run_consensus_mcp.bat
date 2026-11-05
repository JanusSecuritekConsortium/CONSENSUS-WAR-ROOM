@echo off
rem Paths are relative to this file, so the server starts whatever letter the portable SSD has.
cd /d "%~dp0..\.."
"%~dp0..\..\.venv\Scripts\python.exe" "%~dp0consensus_mcp_server.py"
