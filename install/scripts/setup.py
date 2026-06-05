"""Cross-platform setup orchestrator for VoiceTextService.

Runs with system Python (outside venv). Detects OS, creates venv,
installs all dependencies, applies patches, and downloads models.
"""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def _project_root():
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _is_win():
    return sys.platform == "win32"


def _venv_python(root):
    if _is_win():
        return os.path.join(root, ".venv", "Scripts", "python.exe")
    return os.path.join(root, ".venv", "bin", "python3")


def _venv_pip(root):
    return [_venv_python(root), "-m", "pip"]


def _run(cmd, root, **kw):
    description = " ".join(shlex.quote(str(c)) for c in cmd)
    print(f"  > {description}")
    return subprocess.run(cmd, cwd=root, check=True, **kw)


def _run_ok(cmd, root):
    """Run a command, return True on success, False on failure (no exception)."""
    description = " ".join(shlex.quote(str(c)) for c in cmd)
    print(f"  > {description}")
    result = subprocess.run(cmd, cwd=root)
    return result.returncode == 0


def main():
    root = _project_root()
    is_win = _is_win()
    venv_python = _venv_python(root)
    venv_pip = _venv_pip(root)

    print("=" * 60)
    print("  VoiceTextService — Setup")
    if is_win:
        print("  Platform: Windows")
    else:
        print("  Platform: Linux")
    print("=" * 60)
    print()

    # Sentinel check
    sentinel = os.path.join(root, ".setup_done")
    if os.path.exists(sentinel):
        print("Already set up. Delete .setup_done to force reinstall.")
        print()
        if is_win:
            print("Run run\\start_win.bat to launch the server.")
        else:
            print("Run run/start_linux.sh to launch the server.")
        return

    # 1. Check Python
    print("[1/9] Checking Python ...")
    try:
        result = subprocess.run(
            [sys.executable, "--version"], capture_output=True, text=True, check=True)
        print(f"  [OK] {result.stdout.strip()}")
    except Exception:
        print("  [ERROR] Python not found. Install Python 3.10+ and add to PATH.")
        sys.exit(1)
    print()

    # 2. Create virtual environment
    venv_path = os.path.join(root, ".venv")
    if os.path.exists(venv_path):
        print("[2/9] SKIP .venv already exists")
    else:
        print("[2/9] Creating virtual environment .venv ...")
        _run([sys.executable, "-m", "venv", ".venv"], root)
        print("  [OK] .venv created")
    print()

    # 3. Install pip dependencies
    print("[3/9] Installing pip dependencies ...")
    req_path = os.path.join(root, "requirements.txt")
    mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
    if _run_ok(venv_pip + ["install", "-r", req_path, "-i", mirror], root):
        print("  [OK] Dependencies installed")
    else:
        print("  [WARN] Mirror failed, trying default PyPI ...")
        _run(venv_pip + ["install", "-r", req_path], root)
        print("  [OK] Dependencies installed")
    print()

    # 4. Install WeNet (ASR engine)
    print("[4/9] Installing WeNet (ASR) ...")
    result = subprocess.run(
        venv_pip + ["show", "wenet"], capture_output=True, cwd=root)
    if result.returncode == 0:
        print("  [SKIP] wenet already installed")
    else:
        _run(venv_pip + ["install", "git+https://github.com/wenet-e2e/wenet.git"], root)
        print("  [OK] wenet installed")
    print()

    # 5. Install CosyVoice (TTS engine)
    print("[5/9] Installing CosyVoice TTS ...")
    cosyvoice_script = os.path.join(
        root, "install", "scripts", "install_cosyvoice.py")
    _run([venv_python, cosyvoice_script], root)
    print()

    # 6. Apply compatibility patches
    print("[6/9] Applying compatibility patches ...")
    patches_script = os.path.join(
        root, "install", "scripts", "apply_patches.py")
    _run([venv_python, patches_script], root)
    print()

    # 7. Download Paraformer model (ASR)
    print("[7/9] Downloading Paraformer model (~900 MB) ...")
    print("       This may take several minutes on first run.")
    paraformer_dir = os.path.join(root, "pretrained_models", "paraformer")
    paraformer_final = os.path.join(paraformer_dir, "final.pt")
    paraformer_tar = os.path.join(paraformer_dir, "paraformer.tar.gz")

    if os.path.exists(paraformer_final) and os.path.exists(paraformer_tar):
        print("  [SKIP] Paraformer model already in pretrained_models/")
    else:
        # Step A: Let Hub download to ~/.wenet/paraformer/ (skips if already cached)
        hub_cmd = (
            "from wenet.cli.hub import Hub; "
            "print(Hub.download_model('paraformer'))"
        )
        hub_ok = _run_ok([venv_python, "-c", hub_cmd], root)

        # Step B: Copy from ~/.wenet/ to pretrained_models/
        hub_dir = os.path.join(str(Path.home()), ".wenet", "paraformer")
        if hub_ok and os.path.isdir(hub_dir):
            os.makedirs(paraformer_dir, exist_ok=True)
            for name in os.listdir(hub_dir):
                src = os.path.join(hub_dir, name)
                dst = os.path.join(paraformer_dir, name)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
            if os.path.exists(paraformer_final) and os.path.exists(paraformer_tar):
                print("  [OK] Paraformer model ready")
            else:
                print("  [WARN] Copy incomplete. Check pretrained_models/paraformer/")
        else:
            print("  [WARN] Paraformer model download failed. Will auto-download on first server start.")
    print()

    # 8. Download CosyVoice model (TTS)
    print("[8/9] Downloading CosyVoice-300M-SFT model (~1.6 GB) ...")
    print("       This may take several minutes on first run.")
    cosyvoice_model_cmd = (
        "from modelscope import snapshot_download; "
        "snapshot_download("
        "'iic/CosyVoice-300M-SFT', "
        "local_dir='pretrained_models/CosyVoice-300M-SFT', "
        "ignore_file_pattern=["
        "r'\\.zip$', r'\\.onnx$', r'\\.msc$', r'\\.mv$', "
        "r'^\\._____temp', r'^asset/', r'^README\\.md$'"
        "]); "
        "print('OK')"
    )
    if _run_ok([venv_python, "-c", cosyvoice_model_cmd], root):
        print("  [OK] CosyVoice model ready")
    else:
        print("  [WARN] CosyVoice model download failed. Download manually to pretrained_models/CosyVoice-300M-SFT/")
    print()

    # 9. FFmpeg
    print("[9/9] Checking FFmpeg ...")
    if is_win:
        ffmpeg_exe = os.path.join(root, "ffmpeg", "bin", "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            print("  [SKIP] FFmpeg already exists")
        else:
            print("  Downloading FFmpeg (~80 MB) ...")
            ps1_script = os.path.join(
                root, "install", "scripts", "download_ffmpeg.ps1")
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps1_script],
                cwd=root)
            if result.returncode == 0:
                print("  [OK] FFmpeg installed")
            else:
                print("  [WARN] FFmpeg download failed. Only WAV format supported.")
    else:
        # Linux: check if ffmpeg is on PATH
        result = subprocess.run(["which", "ffmpeg"], capture_output=True, cwd=root)
        if result.returncode == 0:
            print(f"  [OK] FFmpeg found: {result.stdout.decode().strip()}")
        else:
            print("  [WARN] FFmpeg not found. Install via: sudo apt install ffmpeg")
            print("         Only WAV format will be supported without FFmpeg.")
    print()

    # Done
    with open(sentinel, "w") as f:
        f.write("")
    print("=" * 60)
    print("  Setup complete!")
    print()
    if is_win:
        print("  Double-click run\\start_win.bat to launch the server.")
    else:
        print("  Run run/start_linux.sh to launch the server.")
    print()
    print("  ASR:  POST http://localhost:8000/asr")
    print("  TTS:  POST http://localhost:8000/tts")
    print("        GET  http://localhost:8000/tts/voices")
    print("  Docs: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
