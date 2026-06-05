"""Install CosyVoice TTS into .venv site-packages.

Clone CosyVoice (with Matcha-TTS submodule) to a temp dir,
copy the packages into the active venv's site-packages, and
install the full set of pip dependencies from the official
requirements.txt (minus conflicting packages already present).

After this script runs, `import cosyvoice` and `import matcha` will work.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile


COSYVOICE_URL = "https://github.com/FunAudioLLM/CosyVoice.git"

# Packages to skip when installing from CosyVoice requirements.txt.
#   - torch / torchaudio: already installed by WeNet (different version)
#   - deepspeed / tensorrt: Linux-only GPU acceleration
#   - gradio / grpcio: web demo / gRPC deployment, not needed for server
#   - fastapi / uvicorn: already in project requirements.txt
SKIP_PACKAGES = {
    "torch",
    "torchaudio",
    "deepspeed",
    "tensorrt-cu12",
    "tensorrt-cu12-bindings",
    "tensorrt-cu12-libs",
    "gradio",
    "grpcio",
    "grpcio-tools",
    "fastapi",
    "fastapi-cli",
    "uvicorn",
    "openai-whisper",
}


def _venv_site_packages():
    """Return path to the active venv's site-packages directory."""
    for p in sys.path:
        if p.endswith("site-packages") and ".venv" in p.replace("\\", "/"):
            return p
    venv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".venv")
    for root, dirs, _ in os.walk(venv):
        if "site-packages" in dirs:
            return os.path.join(root, "site-packages")
    raise RuntimeError("Cannot find .venv site-packages. Run from within the venv.")


def _run(cmd, **kw):
    print(f"  > {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kw)


def _parse_requirements(req_path):
    """Parse a pip requirements.txt, return list of (package_name, line).

    Filters out comments, blank lines, --extra-index-url flags, and
    platform-conditional lines for non-Windows platforms.
    """
    deps = []
    with open(req_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Skip Linux/macOS-only conditionals
            if "; sys_platform ==" in line and "win32" not in line:
                continue
            # Extract package name (strip version specifiers and conditionals)
            pkg_name = re.split(r"[<>=!;]", line)[0].strip()
            deps.append((pkg_name, line))
    return deps


def main():
    print("=" * 50)
    print("  VoiceTextService — Installing CosyVoice TTS")
    print("=" * 50)
    print()

    site_pkg = _venv_site_packages()
    print(f"[INFO] site-packages: {site_pkg}")

    # Locate pip
    pip_exe = os.path.join(os.path.dirname(site_pkg), "..", "Scripts", "pip.exe")
    if not os.path.exists(pip_exe):
        pip = [sys.executable, "-m", "pip"]
    else:
        pip = [pip_exe]

    # Install peft early — silences a diffusers FutureWarning on startup
    try:
        import peft  # noqa: F401
        print("[SKIP] peft already installed")
    except ImportError:
        print("[INFO] Installing peft ...")
        _run(pip + ["install", "peft", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])
    print()

    # Check if cosyvoice packages already installed
    cosyvoice_installed = False
    try:
        import cosyvoice  # noqa: F401
        import matcha    # noqa: F401
        cosyvoice_installed = True
        print("[SKIP] cosyvoice packages already in site-packages")
        print()
    except ImportError:
        pass

    if cosyvoice_installed:
        print("=" * 50)
        print()
        return

    # Clone + install CosyVoice
    tmpdir = tempfile.mkdtemp(prefix="cosyvoice_build_")
    print(f"[INFO] temp dir: {tmpdir}")
    print()

    try:
        print("[1/4] Cloning CosyVoice (with submodules) ...")
        _run(["git", "clone", "--recursive", "--depth", "1", COSYVOICE_URL, tmpdir])
        print()

        print("[2/4] Copying cosyvoice/ to site-packages ...")
        cosyvoice_src = os.path.join(tmpdir, "cosyvoice")
        cosyvoice_dst = os.path.join(site_pkg, "cosyvoice")
        if os.path.exists(cosyvoice_dst):
            shutil.rmtree(cosyvoice_dst)
        shutil.copytree(cosyvoice_src, cosyvoice_dst)
        print()

        print("[3/4] Copying matcha/ to site-packages ...")
        matcha_src = os.path.join(tmpdir, "third_party", "Matcha-TTS", "matcha")
        matcha_dst = os.path.join(site_pkg, "matcha")
        if not os.path.exists(matcha_src):
            print("[WARN] matcha/ submodule not found, retrying init ...")
            _run(["git", "-C", tmpdir, "submodule", "update", "--init", "--recursive"])
            if not os.path.exists(matcha_src):
                raise RuntimeError("matcha/ submodule still missing after retry")
        if os.path.exists(matcha_dst):
            shutil.rmtree(matcha_dst)
        shutil.copytree(matcha_src, matcha_dst)
        print()

        print("[4/4] Installing TTS pip dependencies (from official requirements.txt) ...")
        req_path = os.path.join(tmpdir, "requirements.txt")
        if not os.path.exists(req_path):
            raise RuntimeError("requirements.txt missing from clone")

        all_deps = _parse_requirements(req_path)
        skipped = []
        installed = []
        for pkg_name, spec in all_deps:
            if pkg_name in SKIP_PACKAGES:
                skipped.append(pkg_name)
                print(f"  SKIP {spec:60s} (excluded)")
                continue
            try:
                _run(pip + ["install", spec, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])
                installed.append(pkg_name)
            except subprocess.CalledProcessError:
                print(f"  [WARN] Mirror failed for {spec}, trying default PyPI ...")
                _run(pip + ["install", spec])
                installed.append(pkg_name)

        print()
        print(f"  Installed: {len(installed)} packages")
        print(f"  Skipped:   {len(skipped)} packages ({', '.join(skipped)})")
        print()

    finally:
        print("Cleaning up temp directory ...")
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Verify
    try:
        import cosyvoice  # noqa: F401, F811
        import matcha    # noqa: F401, F811
        print("[OK] cosyvoice installed successfully")
    except ImportError as e:
        print(f"[ERROR] Import verification failed: {e}")
        sys.exit(1)

    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
