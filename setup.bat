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

:: 0. Download FFmpeg (for audio decoding, ~80 MB)
if exist ffmpeg\bin\ffmpeg.exe (
    echo [SKIP] FFmpeg already exists
) else (
    echo [0] Downloading FFmpeg (~80 MB) ...
    powershell -Command "$ProgressPreference='SilentlyContinue'; $u='https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip'; $z='ffmpeg_temp.zip'; Invoke-WebRequest -Uri $u -OutFile $z -UseBasicParsing; Expand-Archive -Path $z -DestinationPath ffmpeg_temp -Force; $bin=Get-ChildItem ffmpeg_temp -Directory | Select-Object -First 1; New-Item -ItemType Directory -Path ffmpeg\bin -Force | Out-Null; Move-Item -Path \"$($bin.FullName)\bin\*\" -Destination ffmpeg\bin -Force; Remove-Item ffmpeg_temp -Recurse -Force; Remove-Item $z -Force; Write-Output 'FFmpeg installed'"
    if %errorlevel% neq 0 (
        echo [WARN] FFmpeg download failed. Only WAV format will be supported.
        echo        To add MP3/M4A support, re-run setup.bat or install FFmpeg manually.
    )
)
echo.

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
    echo [1/6] Creating virtual environment .venv ...
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
echo [2/6] Installing pip dependencies ...
.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [WARN] Mirror failed, trying default PyPI ...
    .venv\Scripts\pip.exe install -r requirements.txt
)
echo.

:: 4. Install wenet from GitHub (skip if already installed)
.venv\Scripts\pip.exe show wenet >nul 2>&1
if %errorlevel% equ 0 (
    echo [3/6] wenet already installed - SKIP
) else (
    echo [3/6] Installing wenet from GitHub ...
    .venv\Scripts\pip.exe install git+https://github.com/wenet-e2e/wenet.git
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install wenet. Check your network and git installation.
        pause
        exit /b 1
    )
)
echo.

:: 5. Apply compatibility patches
echo [4/6] Applying compatibility patches ...
.venv\Scripts\python.exe scripts\apply_patches.py
if %errorlevel% neq 0 (
    echo [ERROR] Patches failed
    pause
    exit /b 1
)
echo.

:: 6. Download Paraformer model (~900 MB)
echo [5/6] Downloading Paraformer model (~900 MB) ...
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
