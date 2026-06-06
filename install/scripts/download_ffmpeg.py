"""Cross-platform FFmpeg auto-downloader for VoiceTextService.

Downloads a prebuilt FFmpeg shared binary from BtbN/FFmpeg-Builds
and extracts it to ffmpeg/bin/ in the project root.

Supports:
  - Windows: win64-gpl-shared.zip
  - Linux:   linux64-gpl-shared.tar.xz
"""

import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path


GITHUB_BASE = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"

IS_WIN = sys.platform == "win32"

if IS_WIN:
    ARCHIVE_NAME = "ffmpeg-master-latest-win64-gpl-shared.zip"
else:
    ARCHIVE_NAME = "ffmpeg-master-latest-linux64-gpl-shared.tar.xz"

DOWNLOAD_URL = f"{GITHUB_BASE}/{ARCHIVE_NAME}"


def _project_root():
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _download(url, dest_path):
    print(f"  Downloading {ARCHIVE_NAME} (~80 MB) ...")
    print(f"  From: {url}")

    def _report(count, block_size, total_size):
        if total_size > 0:
            percent = int(count * block_size * 100 / total_size)
            mb = total_size / (1024 * 1024)
            print(f"\r  Progress: {percent}% of {mb:.0f} MB", end="", flush=True)

    urllib.request.urlretrieve(url, dest_path, reporthook=_report)
    print()


def _unpack_zip(archive_path, extract_dir):
    import zipfile

    print(f"  Extracting ...")
    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(extract_dir)


def _unpack_tar_xz(archive_path, extract_dir):
    import tarfile

    print(f"  Extracting ...")
    with tarfile.open(archive_path, "r:xz") as tf:
        tf.extractall(extract_dir)


def _find_bin_dir(extract_dir):
    """Find the bin/ directory inside the extracted archive tree."""
    for root, dirs, _ in os.walk(extract_dir):
        if os.path.basename(root) == "bin":
            return root
    raise RuntimeError("bin/ directory not found in extracted archive")


def main():
    root = _project_root()
    ffmpeg_bin = os.path.join(root, "ffmpeg", "bin")

    print("=" * 50)
    print("  VoiceTextService — FFmpeg Downloader")
    if IS_WIN:
        print("  Platform: Windows")
    else:
        print("  Platform: Linux")
    print("=" * 50)
    print()

    os.makedirs(ffmpeg_bin, exist_ok=True)

    tmpdir = tempfile.mkdtemp(prefix="ffmpeg_dl_")
    archive_path = os.path.join(tmpdir, ARCHIVE_NAME)
    extract_dir = os.path.join(tmpdir, "extracted")

    try:
        _download(DOWNLOAD_URL, archive_path)

        if IS_WIN:
            _unpack_zip(archive_path, extract_dir)
        else:
            _unpack_tar_xz(archive_path, extract_dir)

        bin_src = _find_bin_dir(extract_dir)

        for name in os.listdir(bin_src):
            src = os.path.join(bin_src, name)
            dst = os.path.join(ffmpeg_bin, name)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

        if not IS_WIN:
            ffmpeg_exe = os.path.join(ffmpeg_bin, "ffmpeg")
            ffprobe_exe = os.path.join(ffmpeg_bin, "ffprobe")
            for exe in (ffmpeg_exe, ffprobe_exe):
                if os.path.exists(exe):
                    os.chmod(exe, 0o755)

        print(f"  [OK] FFmpeg installed to ffmpeg/bin/")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print()


if __name__ == "__main__":
    main()
