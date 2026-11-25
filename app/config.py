"""
Shared constants and application configurations for Gemini AI Plus Portal.
"""

import os
import sys

# Auto-detect build environment:
# - In development/source mode: SHOW_VISUAL_BROWSER_OPTION is True by default.
# - In portable standalone .exe mode: automatically set to False (runs headless in background).
IS_PORTABLE = getattr(sys, "frozen", False) or "__compiled__" in globals()

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # PyInstaller temporary extraction folder for bundled assets
    PROJECT_ROOT = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
    RESULTS_DIR = os.path.join(EXE_DIR, "results")
elif IS_PORTABLE:
    # Nuitka onefile / standalone mode (app/config.py -> parent is bundle root)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
    RESULTS_DIR = os.path.join(EXE_DIR, "results")
else:
    # Source mode (app/config.py -> parent is repository root)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
ICONS_DIR = IMAGES_DIR  # Alias pointing to merged images directory

APP_NAME = "Gemini AI Plus Portal"
APP_VERSION = "v1.0.0"
DEVELOPER_GITHUB_URL = "https://github.com/nmrisrl11"
GITHUB_REPO = "nmrisrl11/gemini-ai-plus-portal"
REPO_GITHUB_URL = f"https://github.com/{GITHUB_REPO}"
UPDATE_MANIFEST_URL = "https://download-ai-plus-portal.nmrisrl.dev/latest/latest.json"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
DOWNLOAD_PAGE_URL = "https://gemini-ai-plus-portal.vercel.app"

# Visual browser checkbox control:
# In development/source mode: SHOW_VISUAL_BROWSER_OPTION is True by default.
# In portable standalone .exe mode: automatically set to False (runs headless in background).
SHOW_VISUAL_BROWSER_OPTION = not IS_PORTABLE

DEFAULT_ACTIVITY_TEXT = """Ready to provision a 1-Year Gemini AI Plus access link.

  1. Enter your target @gmail.com address above.
  2. (Optional) Expand Generated Profile to review or customize details.
  3. Click "Get 1-Year Access Link" to begin automated setup.
  4. Enter the 6-digit verification code sent to your inbox when prompted.
"""
