"""
Cross-platform / Python build script to compile Google AI Plus Portal into an unpackable,
natively compiled standalone .exe using Nuitka.

Produces a true native Windows PE machine-code binary (x86-64) that cannot be unpacked
by pyinstxtractor or Python decompilers.
Usage:
    python build_nuitka.py
"""

import os
import sys
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.config import APP_VERSION

IMAGES_DIR = os.path.join(PROJECT_ROOT, "assets", "images")
ICON_ICO = os.path.join(IMAGES_DIR, "app_icon.ico")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
APP_NAME = f"Google AI Plus Portal {APP_VERSION}"

# Use a local non-synced directory for intermediate build files to prevent
# OneDrive sync lock contention ("Permission denied" on temporary ccache files)
LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
LOCAL_BUILD_DIR = os.path.join(LOCAL_APP_DATA, "NuitkaBuild", "gemini-portal")


def clean_stale_builds():
    """Cleans previous Nuitka intermediate folders to prevent lock contention."""
    search_dirs = [PROJECT_ROOT, DIST_DIR, LOCAL_BUILD_DIR]
    for root in search_dirs:
        if not os.path.exists(root):
            continue
        for item in os.listdir(root):
            if item.endswith(".build") or item.endswith(".dist") or item.endswith(".onefile-build") or item.endswith(".tmp"):
                full_path = os.path.join(root, item)
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path, ignore_errors=True)
                elif os.path.isfile(full_path):
                    try:
                        os.remove(full_path)
                    except OSError:
                        pass

    # Clean stale ccache locks
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        lock_dir = os.path.join(local_app_data, "Nuitka", "Nuitka", "Cache", "ccache", "3.12", "lock")
        if os.path.exists(lock_dir):
            shutil.rmtree(lock_dir, ignore_errors=True)


def build():
    print("=" * 76)
    print(f"   {APP_NAME} — Native C Compiler Packager (Nuitka)")
    print("=" * 76)

    # 1. Verify required icon exists
    if not os.path.exists(ICON_ICO):
        print(f"[*] Icon not found. Generating {ICON_ICO}...")
        from scripts.convert_icon import process_icon
        process_icon()

    # 2. Clean stale build directories
    print("[*] Cleaning stale build caches...")
    clean_stale_builds()
    os.makedirs(DIST_DIR, exist_ok=True)

    # 3. Assemble optimized Nuitka compilation flags
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--assume-yes-for-downloads",
        "--jobs=4",                         # Multi-threaded parallel C compilation
        "--lto=no",                         # Fast linking (skips heavy whole-program LTO)
        "--windows-console-mode=disable",   # GUI application mode (no console window)
        f"--windows-icon-from-ico={ICON_ICO}",
        f"--output-filename={APP_NAME}.exe",
        f"--output-dir={LOCAL_BUILD_DIR}",
        "--enable-plugin=tk-inter",
        "--include-package-data=customtkinter",
        "--include-package-data=playwright",
        "--playwright-include-browser=none", # Lean binary: attaches to system Chrome/Edge/Brave
        f"--include-data-dir={IMAGES_DIR}=assets/images",
        "--windows-company-name=nmrisrl11",
        "--windows-product-name=Google AI Plus Portal",
        "--windows-file-version=1.0.1.0",
        "--windows-product-version=1.0.1.0",
        "--windows-file-description=Google AI Plus (1-Year Access) Portal",
        "--remove-output",
        os.path.join(PROJECT_ROOT, "main.py"),
    ]

    print(f"[*] Starting optimized native compilation for: {APP_NAME}.exe...")
    print(f"    Build engine workspace: {LOCAL_BUILD_DIR}")
    print("    Parallel jobs: 4 CPU cores | Compression: Zstandard | LTO: Disabled")
    print("-" * 76)

    ret = subprocess.call(cmd, cwd=PROJECT_ROOT)

    built_exe = os.path.join(LOCAL_BUILD_DIR, f"{APP_NAME}.exe")
    target_exe = os.path.join(DIST_DIR, f"{APP_NAME}.exe")

    if ret == 0 and os.path.exists(built_exe):
        shutil.copy2(built_exe, target_exe)
        file_size_mb = os.path.getsize(target_exe) / (1024 * 1024)
        print("\n" + "=" * 76)
        print("[OK] HARDENED NATIVE BUILD SUCCESSFUL!")
        print(f"     Target Binary: {target_exe}")
        print(f"     File Size:     {file_size_mb:.2f} MB")
        print("     Security:      Tamper-proof native machine code. pyinstxtractor cannot unpack this.")
        print("=" * 76)
        return True
    else:
        print("\n[!] Nuitka build failed or executable was not produced.")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
