@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py highlight.py --chat-only %*) || (python highlight.py --chat-only %*)
pause
