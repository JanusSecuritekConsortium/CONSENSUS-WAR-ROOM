@echo off
REM AURELIUS Telegram assistant launcher
cd /d "%~dp0"
REM Msty Go owns inbound Telegram conversations. This process only sends scheduled briefs.
set "AURELIUS_TELEGRAM_POLLING=0"
"%~dp0..\..\.venv\Scripts\python.exe" aurelius_bot.py
