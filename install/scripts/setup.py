"""Cross-platform setup orchestrator for VoiceTextService.

Runs with system Python (outside venv). Detects OS, performs pre-flight
assessment, asks user confirmation, then creates venv, installs all
dependencies, applies patches, and downloads models.
"""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Estimated download sizes (MB) — used by assess() and print_assessment()
# ---------------------------------------------------------------------------
SIZE_PIP_DEPS = 20
SIZE_WENET = 350
SIZE_COSYVOICE_SOURCE = 50
SIZE_PARAFORMER = 900
SIZE_COSYVOICE_MODEL = 1600
SIZE_FFMPEG = 80
SIZE_TOTAL = (SIZE_PIP_DEPS + SIZE_WENET + SIZE_COSYVOICE_SOURCE +
              SIZE_PARAFORMER + SIZE_COSYVOICE_MODEL + SIZE_FFMPEG)


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


def _try_import(venv_py, module):
    """Check whether *module* can be imported inside the virtual environment.

    Returns True when ``venv_py -c "import <module>"`` succeeds.
    Safe to call even when venv_py does not exist — returns False.
    """
    if not os.path.exists(venv_py):
        return False
    result = subprocess.run(
        [venv_py, "-c", f"import {module}"], capture_output=True)
    return result.returncode == 0


def assess(root):
    """Scan the project directory and return (status, traffic).

    status : dict[str, str]
        Human-readable labels for each component.
        Keys used by print_assessment():
            python, os, sentinel, venv, core_deps, wenet, cosyvoice,
            paraformer, cosyvoice_model, ffmpeg

    traffic : dict[str, int]
        Keys:  total_if_nothing (SIZE_TOTAL), actual (MB estimated to download)
    """
    is_win = _is_win()
    venv_py = _venv_python(root)
    venv_exists = os.path.exists(venv_py)
    sentinel = os.path.join(root, ".setup_done")

    status = {}
    traffic = {"total_if_nothing": SIZE_TOTAL, "actual": 0}

    # -- System ---------------------------------------------------------------
    pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status["python"] = pyver
    status["os"] = "Windows" if is_win else "Linux"
    status["sentinel"] = "EXISTS" if os.path.exists(sentinel) else "NOT FOUND"

    # -- Virtual environment --------------------------------------------------
    status["venv"] = "EXISTS" if venv_exists else "NOT FOUND"

    # -- Core pip dependencies (requirements.txt) -----------------------------
    core_modules = ["fastapi", "uvicorn", "librosa", "soundfile",
                    "multipart", "numpy"]
    core_total = len(core_modules)
    installed_count = 0
    if venv_exists:
        installed_count = sum(1 for m in core_modules if _try_import(venv_py, m))
        status["core_deps"] = f"{installed_count}/{core_total} installed"
        if installed_count < core_total:
            traffic["actual"] += SIZE_PIP_DEPS
    else:
        status["core_deps"] = "0/6 (venv not created)"
        traffic["actual"] += SIZE_PIP_DEPS

    # -- WeNet ----------------------------------------------------------------
    wenet_ok = _try_import(venv_py, "wenet")
    status["wenet"] = "INSTALLED" if wenet_ok else "NOT INSTALLED"
    if not wenet_ok:
        traffic["actual"] += SIZE_WENET

    # -- CosyVoice ------------------------------------------------------------
    cosy_ok = _try_import(venv_py, "cosyvoice")
    status["cosyvoice"] = "INSTALLED" if cosy_ok else "NOT INSTALLED"
    if not cosy_ok:
        traffic["actual"] += SIZE_COSYVOICE_SOURCE

    # -- Paraformer model -----------------------------------------------------
    pf_dir = os.path.join(root, "pretrained_models", "paraformer")
    pf_model = os.path.exists(os.path.join(pf_dir, "final.pt"))
    pf_tar = os.path.exists(os.path.join(pf_dir, "paraformer.tar.gz"))
    if pf_model and pf_tar:
        status["paraformer"] = "FOUND"
    else:
        # Wenet Hub may have cached the model locally (~/.wenet/paraformer/)
        hub_dir = os.path.join(str(Path.home()), ".wenet", "paraformer")
        hub_has_model = os.path.isdir(hub_dir) and os.path.exists(
            os.path.join(hub_dir, "final.pt"))
        if hub_has_model:
            status["paraformer"] = "CACHED (in ~/.wenet/)"
        else:
            status["paraformer"] = "NOT FOUND"
            traffic["actual"] += SIZE_PARAFORMER

    # -- CosyVoice model ------------------------------------------------------
    cv_dir = os.path.join(root, "pretrained_models", "CosyVoice-300M-SFT")
    cv_yaml = os.path.exists(os.path.join(cv_dir, "cosyvoice.yaml"))
    cv_llm = os.path.exists(os.path.join(cv_dir, "llm.pt"))
    if cv_yaml and cv_llm:
        status["cosyvoice_model"] = "FOUND"
    else:
        status["cosyvoice_model"] = "NOT FOUND"
        traffic["actual"] += SIZE_COSYVOICE_MODEL

    # -- FFmpeg ---------------------------------------------------------------
    ffmpeg_name = "ffmpeg.exe" if is_win else "ffmpeg"
    ffmpeg_path = os.path.join(root, "ffmpeg", "bin", ffmpeg_name)
    ffmpeg_ok = os.path.exists(ffmpeg_path)
    status["ffmpeg"] = "FOUND" if ffmpeg_ok else "NOT FOUND"
    if not ffmpeg_ok:
        traffic["actual"] += SIZE_FFMPEG

    return status, traffic


def _traffic_items(status):
    """Build list of (label, size_mb, is_done) for the traffic report."""
    items = []

    core_done = status["core_deps"].endswith("/6 installed")
    items.append(("Core pip dependencies", SIZE_PIP_DEPS, core_done))

    wenet_done = status["wenet"] == "INSTALLED"
    items.append(("WeNet engine + torch", SIZE_WENET, wenet_done))

    cosy_done = status["cosyvoice"] == "INSTALLED"
    items.append(("CosyVoice source clone", SIZE_COSYVOICE_SOURCE, cosy_done))

    pf_done = status["paraformer"] != "NOT FOUND"
    items.append(("Paraformer model", SIZE_PARAFORMER, pf_done))

    cv_done = status["cosyvoice_model"] == "FOUND"
    items.append(("CosyVoice-300M-SFT model", SIZE_COSYVOICE_MODEL, cv_done))

    ffmpeg_done = status["ffmpeg"] == "FOUND"
    items.append(("FFmpeg binaries", SIZE_FFMPEG, ffmpeg_done))

    return items


def print_assessment(status, traffic):
    """Display formatted pre-flight assessment report."""

    bar = "=" * 60
    sub = "-" * 60

    print()
    print(bar)
    print("  VoiceTextService - Pre-flight Assessment")
    print(bar)
    print()

    # System
    print("  System")
    print(f"    Python ....................... {status['python']}")
    print(f"    OS ............................ {status['os']}")
    print()

    # Environment
    print("  Environment")
    print(f"    Virtual env (.venv) ........... {status['venv']}")
    print(f"    Setup sentinel (.setup_done) .. {status['sentinel']}")
    print()

    # Python Packages
    print("  Python Packages")
    print(f"    Core deps (requirements.txt) .. {status['core_deps']}")
    print(f"    WeNet (ASR engine) ............ {status['wenet']}")
    print(f"    CosyVoice (TTS engine) ........ {status['cosyvoice']}")
    print()

    # Models
    print("  Models (pretrained_models/)")
    print(f"    Paraformer (~900 MB) .......... {status['paraformer']}")
    print(f"    CosyVoice-300M-SFT (~1.6 GB) .. {status['cosyvoice_model']}")
    print()

    # Tools
    print("  Tools")
    print(f"    FFmpeg (~80 MB) ............... {status['ffmpeg']}")
    print()

    # Traffic
    print(sub)
    print("  Estimated Download Traffic")
    print(sub)

    items = _traffic_items(status)
    total = sum(sz for _, sz, done in items if not done)

    fmt = "  {label:<38s} {size:>5d} MB {tag}"
    for label, size, done in items:
        tag = "(skipped)" if done else ""
        size_display = 0 if done else size
        print(fmt.format(label=label, size=size_display, tag=tag))

    print(f"  {'-' * 50}")
    print(f"  {'Total if nothing cached':<38s} {SIZE_TOTAL:>5d} MB")
    print(f"  {'Estimated actual':<38s} {total:>5d} MB")
    print(bar)
    print()


def confirm():
    """Prompt user for Y/n confirmation. Returns True on Y/yes/<Enter>."""
    while True:
        try:
            answer = input("  Proceed with installation? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Installation cancelled.")
            return False

        if answer in ("", "y", "yes"):
            print()
            return True
        if answer in ("n", "no"):
            print("\n  Installation cancelled.")
            return False
        print('  Please enter Y (yes) or N (no).')


def do_install(is_win, root, venv_python, venv_pip):
    """Run all 9 installation steps (called only after user confirms)."""

    # 1. Check Python
    print("[1/9] Checking Python ...")
    result = subprocess.run(
        [sys.executable, "--version"], capture_output=True, text=True, check=True)
    print(f"  [OK] {result.stdout.strip()}")
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
        _run(venv_pip + ["install",
             "git+https://github.com/wenet-e2e/wenet.git"], root)
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
        hub_cmd = (
            "from wenet.cli.hub import Hub; "
            "print(Hub.download_model('paraformer'))"
        )
        hub_ok = _run_ok([venv_python, "-c", hub_cmd], root)

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
            print("  [WARN] Paraformer model download failed. "
                  "Will auto-download on first server start.")
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
        print("  [WARN] CosyVoice model download failed. "
              "Download manually to pretrained_models/CosyVoice-300M-SFT/")
    print()

    # 9. FFmpeg
    print("[9/9] Checking FFmpeg ...")
    if is_win:
        ffmpeg_exe = os.path.join(root, "ffmpeg", "bin", "ffmpeg.exe")
    else:
        ffmpeg_exe = os.path.join(root, "ffmpeg", "bin", "ffmpeg")
    if os.path.exists(ffmpeg_exe):
        print("  [SKIP] FFmpeg already exists in ffmpeg/bin/")
    else:
        print("  Downloading FFmpeg (~80 MB) ...")
        ffmpeg_script = os.path.join(
            root, "install", "scripts", "download_ffmpeg.py")
        result = subprocess.run(
            [sys.executable, ffmpeg_script], cwd=root)
        if result.returncode == 0:
            print("  [OK] FFmpeg installed to ffmpeg/bin/")
        else:
            print("  [WARN] FFmpeg download failed. Only WAV format supported.")
    print()

    # Done
    sentinel = os.path.join(root, ".setup_done")
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


def main():
    root = _project_root()
    is_win = _is_win()

    # Banner
    print("=" * 60)
    print("  VoiceTextService - Setup")
    sys.stdout.flush()

    # Sentinel check (existing setup is a one-line shortcut)
    sentinel = os.path.join(root, ".setup_done")
    if os.path.exists(sentinel):
        print("  Already set up. Delete .setup_done to force reinstall.")
        print()
        if is_win:
            print("  Run run\\start_win.bat to launch the server.")
        else:
            print("  Run run/start_linux.sh to launch the server.")
        return

    # Check system Python
    try:
        result = subprocess.run(
            [sys.executable, "--version"], capture_output=True, text=True, check=True)
        pyver = result.stdout.strip()
    except Exception:
        print("  [ERROR] Python not found. Install Python 3.10+ and add to PATH.")
        sys.exit(1)

    print(f"  System Python: {pyver}")
    if is_win:
        print("  Platform: Windows")
    else:
        print("  Platform: Linux")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Pre-flight assessment
    # ------------------------------------------------------------------
    print()
    print("  Running pre-flight assessment ...")
    status, traffic = assess(root)
    print_assessment(status, traffic)

    # ------------------------------------------------------------------
    # User confirmation
    # ------------------------------------------------------------------
    if not confirm():
        sys.exit(0)

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------
    print("=" * 60)
    print("  VoiceTextService - Installation")
    print("=" * 60)
    print()

    venv_python = _venv_python(root)
    venv_pip = _venv_pip(root)
    do_install(is_win, root, venv_python, venv_pip)


if __name__ == "__main__":
    main()
