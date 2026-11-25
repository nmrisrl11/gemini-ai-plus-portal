"""
Cross-platform / Python build script to compile Gemini AI Plus Portal into a
hardened, natively compiled Windows binary using Nuitka.

Produces true native Windows PE machine-code binaries (x86-64) that cannot be
unpacked by pyinstxtractor or Python decompilers.

Usage:
    python scripts/build_nuitka.py                    # Default: single-file compressed .exe (onefile)
    python scripts/build_nuitka.py --mode standalone  # Optional: standalone folder + portable .zip
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.config import APP_NAME as PORTAL_NAME, APP_VERSION

IMAGES_DIR = os.path.join(PROJECT_ROOT, "assets", "images")
ICON_ICO = os.path.join(IMAGES_DIR, "app_icon.ico")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
APP_NAME = f"{PORTAL_NAME} {APP_VERSION}"

# Runtime-only images (excludes unused logo_raw.jpg ~1.82 MB and preview.PNG)
RUNTIME_IMAGE_FILES = (
    "app_icon.ico",
    "app_icon.png",
    "check.png",
    "shuffle.png",
    "qrcode-bmc.png",
    "qrcode-gcash.JPG",
)


def _to_windows_pe_version(version_str: str) -> str:
    """Converts a semver tag like 'v1.0.0' into 4-part Windows PE version '1.0.0.0'."""
    raw = version_str.lstrip("vV").strip()
    parts = [p for p in raw.split(".") if p.isdigit()]
    while len(parts) < 4:
        parts.append("0")
    return ".".join(parts[:4])


PE_VERSION = _to_windows_pe_version(APP_VERSION)


def _resolve_build_dir() -> str:
    """
    Returns a non-OneDrive, space-free build directory on Windows so MinGW ld.exe
    response files (@./@link_input.txt) never fail due to spaces in user profiles.
    """
    env_override = os.environ.get("NUITKA_BUILD_DIR", "").strip()
    if env_override:
        return env_override

    if sys.platform == "win32":
        system_drive = os.environ.get("SystemDrive", "C:")
        candidate = os.path.join(f"{system_drive}\\", "NuitkaBuild", "gemini-portal")
        try:
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except OSError:
            pass

    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(local_app_data, "NuitkaBuild", "gemini-portal")


LOCAL_BUILD_DIR = _resolve_build_dir()


def compute_sha256(file_path: str) -> str:
    """Computes the uppercase SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def clean_stale_builds():
    """Cleans previous Nuitka intermediate folders to prevent lock contention."""
    search_dirs = [PROJECT_ROOT, DIST_DIR, LOCAL_BUILD_DIR]
    for root in search_dirs:
        if not os.path.exists(root):
            continue
        for item in os.listdir(root):
            if (
                item.endswith(".build")
                or item.endswith(".dist")
                or item.endswith(".onefile-build")
                or item.endswith(".tmp")
            ):
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


def _zip_directory(source_dir: str, zip_path: str, root_folder_name: str):
    """Creates a clean portable ZIP archive with a top-level folder."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for dirpath, _dirnames, filenames in os.walk(source_dir):
            for fname in filenames:
                abs_file = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_file, source_dir)
                arcname = os.path.join(root_folder_name, rel_path)
                zf.write(abs_file, arcname)


def build(mode: str = "onefile", jobs: int = 4) -> bool:
    mode = mode.lower().strip()
    print("=" * 76)
    print(f"   {APP_NAME} — Native C Compiler Packager (Nuitka | mode={mode})")
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
    os.makedirs(LOCAL_BUILD_DIR, exist_ok=True)

    # 3. Assemble optimized Nuitka compilation flags
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--mingw64",
        "--low-memory",
        "--assume-yes-for-downloads",
        f"--jobs={jobs}",
        "--lto=no",
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={ICON_ICO}",
        f"--output-filename={APP_NAME}.exe",
        f"--output-dir={LOCAL_BUILD_DIR}",
        "--enable-plugin=tk-inter",
        "--include-package-data=customtkinter",
        "--include-package-data=playwright",
        "--playwright-include-browser=none",
        "--windows-company-name=nmrisrl11",
        f"--windows-product-name={PORTAL_NAME}",
        f"--windows-file-version={PE_VERSION}",
        f"--windows-product-version={PE_VERSION}",
        f"--windows-file-description={PORTAL_NAME}",
        "--remove-output",
    ]

    if mode == "onefile":
        cmd.append("--onefile")

    # Bundle only runtime-needed image assets (exclude logo_raw.jpg & preview.PNG)
    for img_name in RUNTIME_IMAGE_FILES:
        src_img = os.path.join(IMAGES_DIR, img_name)
        if os.path.exists(src_img):
            cmd.append(f"--include-data-file={src_img}=assets/images/{img_name}")

    cmd.append(os.path.join(PROJECT_ROOT, "main.py"))

    print(f"[*] Starting native compilation for: {APP_NAME} ({mode})...")
    print(f"    Build engine workspace: {LOCAL_BUILD_DIR}")
    print(f"    Parallel jobs: {jobs} CPU cores | LTO: Disabled | Runtime assets: {len(RUNTIME_IMAGE_FILES)} files")
    print("-" * 76)

    ret = subprocess.call(cmd, cwd=PROJECT_ROOT)
    if ret != 0:
        print("\n[!] Nuitka build failed.")
        return False

    if mode == "onefile":
        built_exe = os.path.join(LOCAL_BUILD_DIR, f"{APP_NAME}.exe")
        target_exe = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
        if os.path.exists(built_exe):
            shutil.copy2(built_exe, target_exe)
            file_size_mb = os.path.getsize(target_exe) / (1024 * 1024)
            sha256 = compute_sha256(target_exe)
            print("\n" + "=" * 76)
            print("[OK] HARDENED NATIVE ONEFILE BUILD SUCCESSFUL!")
            print(f"     Target Binary: {target_exe}")
            print(f"     File Size:     {file_size_mb:.2f} MB")
            print(f"     SHA-256:       {sha256}")
            print("=" * 76)
            return True
    else:
        built_dist_dir = os.path.join(LOCAL_BUILD_DIR, "main.dist")
        target_folder = os.path.join(DIST_DIR, APP_NAME)
        target_zip = os.path.join(DIST_DIR, f"{APP_NAME}-win64.zip")
        if os.path.isdir(built_dist_dir):
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder, ignore_errors=True)
            shutil.copytree(built_dist_dir, target_folder)
            if os.path.exists(target_zip):
                os.remove(target_zip)
            _zip_directory(target_folder, target_zip, APP_NAME)

            exe_inside = os.path.join(target_folder, f"{APP_NAME}.exe")
            zip_size_mb = os.path.getsize(target_zip) / (1024 * 1024)
            zip_sha256 = compute_sha256(target_zip)
            exe_sha256 = compute_sha256(exe_inside) if os.path.exists(exe_inside) else "N/A"
            print("\n" + "=" * 76)
            print("[OK] HARDENED NATIVE STANDALONE BUILD SUCCESSFUL!")
            print(f"     Portable Folder: {target_folder}")
            print(f"     Release Archive: {target_zip}")
            print(f"     Archive Size:    {zip_size_mb:.2f} MB")
            print(f"     ZIP SHA-256:     {zip_sha256}")
            print(f"     EXE SHA-256:     {exe_sha256}")
            print("=" * 76)
            return True

    print("\n[!] Expected build output was not produced.")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Gemini AI Plus Portal with Nuitka")
    parser.add_argument(
        "--mode",
        choices=["onefile", "standalone"],
        default="onefile",
        help="Build mode: 'onefile' (single portable .exe, default) or 'standalone' (folder + .zip)",
    )
    parser.add_argument("--jobs", type=int, default=4, help="Parallel C compilation jobs (default: 4)")
    args = parser.parse_args()
    success = build(mode=args.mode, jobs=args.jobs)
    sys.exit(0 if success else 1)
