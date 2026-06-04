@echo off
title VoiceTextService
echo ========================================
echo   VoiceTextService - ASR Backend
echo ========================================
echo.

set PATH=%CD%\ffmpeg\bin;%PATH%

call .venv\Scripts\activate.bat

echo Starting server on http://0.0.0.0:8000 ...
echo Press Ctrl+C to stop
echo.

python src\server.py

pause
