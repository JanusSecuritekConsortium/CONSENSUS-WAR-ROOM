@echo off
setlocal
cd /d "%~dp0"
set OLLAMA_BASE_URL=http://127.0.0.1:11964
python consensus_war_room_genesis.py --api --backend msty-local --theme eva
pause
