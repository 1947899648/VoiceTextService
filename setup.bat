@echo off
title VoiceTextService - Setup
echo ========================================
echo   VoiceTextService - Setup
echo ========================================
echo.

:: Skip everything if already set up
if exist .setup_done (
    echo Already set up. Delete .setup_done to force reinstall.
    echo.
    echo Run start.bat to launch the server.
    pause
    exit /b 0
)

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    pause
    exit /b 1
)
echo [OK] Python found
echo.

:: 2. Create virtual environment
if exist .venv\ (
    echo [SKIP] .venv already exists
) else (
    echo [1/5] Creating virtual environment .venv ...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo [OK] .venv created
)
echo.

:: 3. Install pip dependencies
echo [2/5] Installing pip dependencies ...
.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [WARN] Mirror failed, trying default PyPI ...
    .venv\Scripts\pip.exe install -r requirements.txt
)
echo.

:: 4. Install wenet from GitHub (skip if already installed)
.venv\Scripts\pip.exe show wenet >nul 2>&1
if %errorlevel% equ 0 (
    echo [3/5] wenet already installed - SKIP
) else (
    echo [3/5] Installing wenet from GitHub ...
    .venv\Scripts\pip.exe install git+https://github.com/wenet-e2e/wenet.git
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install wenet. Check your network and git installation.
        pause
        exit /b 1
    )
)
echo.

:: 5. Apply compatibility patches
echo [4/5] Applying compatibility patches ...
.venv\Scripts\python.exe scripts\apply_patches.py
if %errorlevel% neq 0 (
    echo [ERROR] Patches failed
    pause
    exit /b 1
)
echo.

:: 6. Download Paraformer model (~900 MB)
echo [5/5] Downloading Paraformer model (~900 MB) ...
echo        This may take several minutes on first run.
.venv\Scripts\python.exe -c "from wenet.cli.hub import Hub; print(Hub.download_model('paraformer'))"
if %errorlevel% neq 0 (
    echo [WARN] Model download failed. It will auto-download on first server start.
)
echo.

:: Mark setup as complete
echo. > .setup_done

echo ========================================
echo   Setup complete!
echo.
echo   Double-click start.bat to run the server.
echo.
echo   API:    POST http://localhost:8000/asr
echo   Docs:   http://localhost:8000/docs
echo ========================================
pause
