@echo off
title VoiceTextService - Setup
echo ========================================
echo   VoiceTextService - Setup
echo ========================================
echo.

:: Sentinel check
if exist .setup_done goto ALREADY_DONE

:: 0. FFmpeg
if exist ffmpeg\bin\ffmpeg.exe goto FFMPEG_SKIP
echo [0] Downloading FFmpeg (~80 MB) ...
powershell -ExecutionPolicy Bypass -File scripts\download_ffmpeg.ps1
if not errorlevel 1 goto FFMPEG_DONE
echo [WARN] FFmpeg download failed. Only WAV format supported.
goto FFMPEG_DONE
:FFMPEG_SKIP
echo [SKIP] FFmpeg already exists
:FFMPEG_DONE
echo.

:: 1. Python
echo [1/8] Checking Python ...
python --version >nul 2>&1
if errorlevel 1 goto ERR_PYTHON
echo [OK] Python found
echo.

:: 2. Virtual environment
if exist .venv\ goto VENV_SKIP
echo [2/8] Creating virtual environment .venv ...
python -m venv .venv
if errorlevel 1 goto ERR_VENV
echo [OK] .venv created
goto VENV_DONE
:VENV_SKIP
echo [SKIP] .venv already exists
:VENV_DONE
echo.

:: 3. Pip dependencies
echo [3/8] Installing pip dependencies ...
.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if not errorlevel 1 goto PIP_DONE
echo [WARN] Mirror failed, trying default PyPI ...
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 goto ERR_PIP
:PIP_DONE
echo.

:: 4. WeNet (ASR engine)
.venv\Scripts\pip.exe show wenet >nul 2>&1
if not errorlevel 1 goto WENET_SKIP
echo [4/8] Installing wenet from GitHub ...
.venv\Scripts\pip.exe install git+https://github.com/wenet-e2e/wenet.git
if errorlevel 1 goto ERR_WENET
goto WENET_DONE
:WENET_SKIP
echo [4/8] wenet already installed - SKIP
:WENET_DONE
echo.

:: 5. CosyVoice (TTS engine)
echo [5/8] Installing CosyVoice TTS ...
.venv\Scripts\python.exe scripts\install_cosyvoice.py
if errorlevel 1 goto ERR_COSYVOICE
echo.

:: 6. Patches (WeNet + CosyVoice)
echo [6/8] Applying compatibility patches ...
.venv\Scripts\python.exe scripts\apply_patches.py
if errorlevel 1 goto ERR_PATCH
echo.

:: 7. Paraformer model (ASR)
echo [7/8] Downloading Paraformer model (~900 MB) ...
echo        This may take several minutes on first run.
.venv\Scripts\python.exe -c "from wenet.cli.hub import Hub; print(Hub.download_model('paraformer'))"
if not errorlevel 1 goto ASR_MODEL_DONE
echo [WARN] Paraformer model download failed. Will auto-download on first server start.
:ASR_MODEL_DONE
echo.

:: 8. CosyVoice model (TTS)
echo [8/8] Downloading CosyVoice-300M-SFT model (~1.5 GB) ...
echo        This may take several minutes on first run.
.venv\Scripts\python.exe -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice-300M-SFT', local_dir='pretrained_models/CosyVoice-300M-SFT'); print('OK')"
if not errorlevel 1 goto TTS_MODEL_DONE
echo [WARN] CosyVoice model download failed. Download manually to pretrained_models/CosyVoice-300M-SFT/
:TTS_MODEL_DONE
echo.

:: Done
echo. > .setup_done
echo ========================================
echo   Setup complete!
echo.
echo   Double-click start.bat to run the server.
echo.
echo   ASR:  POST http://localhost:8000/asr
echo   TTS:  POST http://localhost:8000/tts
echo         GET  http://localhost:8000/tts/voices
echo   Docs: http://localhost:8000/docs
echo ========================================
pause
exit /b 0

:ALREADY_DONE
echo Already set up. Delete .setup_done to force reinstall.
echo.
echo Run start.bat to launch the server.
pause
exit /b 0

:ERR_PYTHON
echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
pause
exit /b 1

:ERR_VENV
echo [ERROR] Failed to create virtual environment.
pause
exit /b 1

:ERR_PIP
echo [ERROR] Failed to install pip dependencies.
pause
exit /b 1

:ERR_WENET
echo [ERROR] Failed to install wenet. Check network and git.
pause
exit /b 1

:ERR_COSYVOICE
echo [ERROR] Failed to install CosyVoice TTS. Check network and git.
pause
exit /b 1

:ERR_PATCH
echo [ERROR] Patch application failed.
pause
exit /b 1
