"""
Shared constants and application configurations for Google AI Plus Portal.
"""

import os
import sys

# Auto-detect build environment:
# - In development/source mode: SHOW_VISUAL_BROWSER_OPTION is True by default.
# - In portable standalone .exe mode: automatically set to False (runs headless in background).
IS_PORTABLE = getattr(sys, "frozen", False)

if IS_PORTABLE:
    # PyInstaller temporary extraction folder for bundled assets
    PROJECT_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    # Persistent directory next to the standalone executable for output credentials and logs
    EXE_DIR = os.path.dirname(sys.executable)
    RESULTS_DIR = os.path.join(EXE_DIR, "results")
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

IMAGES_DIR = os.path.join(PROJECT_ROOT, "images")
ICONS_DIR = IMAGES_DIR  # Alias pointing to merged images directory

APP_VERSION = "v1.0.0"
DEVELOPER_GITHUB_URL = "https://github.com/nmrisrl11"

SHOW_VISUAL_BROWSER_OPTION = True

DEFAULT_ACTIVITY_TEXT = """================================================================================
  GOOGLE AI PLUS — 1-YEAR ACCESS PROVISIONER
================================================================================
  Status: System Ready

  Quick Guide:
  1. Review or customize your account profile above.
  2. Click "Get 1-Year Access Link" to start provisioning.
  3. Enter the 6-digit verification code sent to your email when prompted.
  4. Your 1-Year Google AI Plus redemption link will be ready to claim!
================================================================================
"""
