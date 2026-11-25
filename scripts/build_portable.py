"""
Cross-platform / Python build script to compile Google AI Plus Portal into a portable .exe.
Usage:
    python build_portable.py
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
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
APP_NAME = f"Google AI Plus Portal {APP_VERSION}"


def build():
    print("=" * 72)
    print(f"   {APP_NAME} — Portable Standalone Packager")
    print("=" * 72)

    # 1. Verify required icon exists
    if not os.path.exists(ICON_ICO):
        print(f"[!] Warning: {ICON_ICO} not found. Running convert_icon.py first...")
        from scripts.convert_icon import process_icon
        process_icon()

    # 2. Clean previous build folders
    print("[*] Cleaning build directories...")
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    # 3. Assemble PyInstaller arguments
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name",
        APP_NAME,
        f"--icon={ICON_ICO}",
        f"--add-data={IMAGES_DIR};assets/images",
        "--collect-all",
        "customtkinter",
        "--collect-all",
        "playwright",
        "--clean",
        os.path.join(PROJECT_ROOT, "main.py"),
    ]

    print(f"[*] Running PyInstaller compilation for: {APP_NAME}.exe...")
    ret = subprocess.call(cmd, cwd=PROJECT_ROOT)
    
    exe_target = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    if ret == 0 and os.path.exists(exe_target):
        print("\n" + "=" * 72)
        print("[OK] BUILD SUCCESSFUL!")
        print(f"     Portable Executable: {exe_target}")
        print("=" * 72)
        return True
    else:
        print("\n[!] Build failed or executable was not produced.")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
