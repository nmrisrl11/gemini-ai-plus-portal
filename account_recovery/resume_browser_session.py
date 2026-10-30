"""
Multi-Browser Account Recovery & Profile Completion Tool
========================================================
Safety Net Tool: Resumes uncompleted user accounts directly inside an existing,
authenticated browser session (Google Chrome, Brave Browser, or Microsoft Edge).
Bypasses front-door login / verification barriers by attaching to the active browser context
over Chrome DevTools Protocol (CDP).

Adapted with flexible browser discovery and graceful session restoration.
"""

import os
import sys
import json
import time
import socket
import subprocess
from typing import Dict, Optional

# Resolve project root (parent directory of account_recovery)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from playwright.sync_api import sync_playwright
from claimer import GeminiAIClaimer

CDP_PORT = 9222
TARGET_URL = "https://internshala.com/user_preference/preferences"

SUPPORTED_BROWSERS = {
    "brave": {
        "name": "Brave Browser",
        "process_name": "brave.exe",
        "paths": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ],
        "pref_path": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Preferences"),
    },
    "chrome": {
        "name": "Google Chrome",
        "process_name": "chrome.exe",
        "paths": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "pref_path": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Preferences"),
    },
    "edge": {
        "name": "Microsoft Edge",
        "process_name": "msedge.exe",
        "paths": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ],
        "pref_path": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Preferences"),
    },
}


def is_port_open(port: int = CDP_PORT, host: str = "127.0.0.1") -> bool:
    """Check if the remote debugging port is open and listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host, port)) == 0


def get_installed_browsers() -> Dict[str, Dict]:
    """Scans the system for installed supported browsers."""
    installed = {}
    for key, info in SUPPORTED_BROWSERS.items():
        for path in info["paths"]:
            if os.path.exists(path):
                installed[key] = {**info, "path": path}
                break
    return installed


def is_process_running(process_name: str) -> bool:
    """Check if a specific process is currently running on Windows."""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        return process_name.lower() in output.lower()
    except Exception:
        return False


def graceful_close_browser(process_name: str, timeout: float = 3.5):
    """
    Gracefully asks the browser windows to close so all tabs and session state are preserved.
    Avoids abrupt termination which triggers the crash prompt.
    """
    # 1. Send graceful WM_CLOSE via taskkill (without /F)
    try:
        subprocess.run(
            ["taskkill", "/IM", process_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

    # Wait for the browser process to write session files and exit cleanly
    start = time.time()
    while time.time() - start < timeout:
        if not is_process_running(process_name):
            return True
        time.sleep(0.4)

    # 2. If background helper processes linger after timeout, clean them up
    try:
        subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.0)
    except Exception:
        pass
    return True


def clean_browser_exit_state(browser_key: str):
    """Ensures the browser profile preferences don't trigger the 'crashed' dialog."""
    pref_file = SUPPORTED_BROWSERS.get(browser_key, {}).get("pref_path")
    if pref_file and os.path.exists(pref_file):
        try:
            with open(pref_file, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            modified = False
            if "profile" in data:
                if data["profile"].get("exit_type") != "Normal":
                    data["profile"]["exit_type"] = "Normal"
                    modified = True
                if data["profile"].get("exited_cleanly") is False:
                    data["profile"]["exited_cleanly"] = True
                    modified = True
            if modified:
                with open(pref_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
        except Exception:
            pass


def ensure_browser_session(chosen_browser: Optional[str] = None) -> bool:
    """
    Ensures that a browser is active and listening on the CDP debugging port.
    If not open, offers to launch or restart the chosen browser automatically.
    """
    if is_port_open(CDP_PORT):
        print(f"[+] Active browser session detected on debug port {CDP_PORT}!")
        return True

    installed = get_installed_browsers()
    if not installed:
        print("[!] Could not auto-detect any supported browsers (Brave, Chrome, Edge).")
        return False

    selected_key = chosen_browser
    if not selected_key or selected_key not in installed:
        # Check if an installed browser is already running
        running_keys = [k for k, v in installed.items() if is_process_running(v["process_name"])]
        if len(running_keys) == 1:
            selected_key = running_keys[0]
            print(f"[+] Detected active {installed[selected_key]['name']} session.")
        else:
            print("\n" + "=" * 60)
            print("        BROWSER SELECTION & AUTO-CONNECT")
            print("=" * 60)
            print("Which browser has your active session?")
            browser_keys = list(installed.keys())
            for idx, key in enumerate(browser_keys, 1):
                info = installed[key]
                tag = " (Active)" if key in running_keys else ""
                print(f"  [{idx}] {info['name']}{tag}")

            choice_str = input(f"Enter choice [1-{len(browser_keys)}] (Default 1): ").strip()
            try:
                choice_idx = int(choice_str) - 1 if choice_str else 0
                if 0 <= choice_idx < len(browser_keys):
                    selected_key = browser_keys[choice_idx]
                else:
                    selected_key = browser_keys[0]
            except Exception:
                selected_key = browser_keys[0]

    browser_info = installed[selected_key]
    print(f"\n[+] Preparing {browser_info['name']} for CDP automation...")

    # If the browser is running without debugging port, close it gracefully to re-open with debug port
    if is_process_running(browser_info["process_name"]):
        print(f"[*] Closing running {browser_info['name']} windows to apply debugging flag...")
        graceful_close_browser(browser_info["process_name"])
        clean_browser_exit_state(selected_key)
        time.sleep(1.0)

    # Launch with remote debugging
    cmd = [
        browser_info["path"],
        f"--remote-debugging-port={CDP_PORT}",
        "--restore-last-session",
        "--disable-session-crashed-bubble",
        TARGET_URL,
    ]
    print(f"[*] Launching {browser_info['name']} on port {CDP_PORT} (restoring open tabs)...")
    try:
        subprocess.Popen(cmd)
        for _ in range(20):
            time.sleep(0.5)
            if is_port_open(CDP_PORT):
                print(f"[+] {browser_info['name']} successfully connected on port {CDP_PORT}!")
                return True
        print("[!] Timed out waiting for browser debugging port.")
        return False
    except Exception as e:
        print(f"[!] Error launching browser: {e}")
        return False


def run_recovery(browser_choice: Optional[str] = None):
    print("================================================================")
    print("  Account Recovery Safety Net: Profile Completer")
    print("================================================================")

    if not ensure_browser_session(browser_choice):
        print("[ERROR] Could not establish connection with browser debugging session.")
        return False

    print("\nConnecting automation engine to your active browser context...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        except Exception as e:
            print(f"[ERROR] Could not connect over CDP: {e}")
            return False

        context = browser.contexts[0]
        print(f"Connected! Inspecting {len(context.pages)} open tab(s)...")

        # Find or navigate to personal_details / onboarding
        target_page = None
        for page in context.pages:
            try:
                if "internshala.com" in page.url:
                    target_page = page
                    print("Found active authenticated session tab.")
                    break
            except Exception:
                pass

        if not target_page:
            print("Opening career preferences portal...")
            target_page = context.new_page()
            target_page.goto(TARGET_URL, wait_until="domcontentloaded")
            target_page.wait_for_timeout(3000)
        else:
            if (
                "personal_details" not in target_page.url
                and "onboarding" not in target_page.url
                and "preferences" not in target_page.url
                and "internships" not in target_page.url
                and "google-gemini-ai-plus" not in target_page.url
            ):
                print("Navigating tab to career preferences portal...")
                target_page.goto(TARGET_URL, wait_until="domcontentloaded")
                target_page.wait_for_timeout(3000)

        claimer = GeminiAIClaimer(
            email="browser_recovery@authenticated.local",
            password="",
            mode="login",
            headless=False,
            allow_manual_verification=True,
        )

        # Step 1: Personal Details (only if actually on onboarding/personal_details)
        if (
            "personal_details" in target_page.url
            or "onboarding" in target_page.url
            or target_page.locator(":has-text(\"Let's get started\")").first.is_visible()
        ):
            print("\n-------------------------------------------------------")
            print("  STEP 1: AUTO-FILLING PROFILE ONBOARDING DETAILS")
            print("-------------------------------------------------------")
            target_page.wait_for_timeout(1000)
            success_profile = claimer._step_profile_details(target_page)
            print(f"[Result] Profile details completion status: {success_profile}")

            if not success_profile:
                print("\n[ERROR] Form could not pass validation. Please inspect your open browser tab.")
                return False
        else:
            print("\n[INFO] Profile onboarding details already completed. Proceeding directly...")

        # Step 2: Preferences (if on preferences or not yet on matching-preferences)
        if (
            "matching-preferences" not in target_page.url
            and "google-gemini-ai-plus" not in target_page.url
        ):
            print("\n-------------------------------------------------------")
            print("  STEP 2: AUTO-FILLING PREFERENCES")
            print("-------------------------------------------------------")
            target_page.wait_for_timeout(1000)
            success_pref = claimer._step_preferences(target_page)
            print(f"[Result] Preferences completion status: {success_pref}")

            if not success_pref:
                print("\n[ERROR] Preferences step encountered an issue.")
                return False
        else:
            print("\n[INFO] Preferences already completed. Proceeding directly to offer claim...")

        print("\n-------------------------------------------------------")
        print("  STEP 3: CLAIMING 12-MONTH FREE GEMINI PLUS PROMO LINK")
        print("-------------------------------------------------------")
        redemption_url = claimer._step_claim_gemini(target_page, context)

        # Attempt to detect session email for saving record
        session_email = None
        try:
            session_email = target_page.evaluate("""() => {
                const el = document.querySelector('[data-email], .user_email, .profile-email, .dropdown-menu .email');
                if (el && el.textContent) return el.textContent.trim();
                return null;
            }""")
        except Exception:
            pass
        session_email = session_email or "recovered_account@user.local"

        if redemption_url == "EMAIL_DISPATCHED":
            try:
                from gui import save_result_file
                save_result_file(
                    email=session_email,
                    password="(Existing Authenticated Session)",
                    name="Recovered Account",
                    phone="N/A",
                    url="EMAIL_DISPATCHED",
                )
            except Exception:
                pass

            print("\n" + "=" * 68)
            print("  [SUCCESS] ACCOUNT SETUP COMPLETED SUCCESSFULLY!")
            print("=" * 68)
            print("\nYour profile has been fully completed and qualified.")
            print("The activation and redemption link has been sent directly")
            print("to your registered email address.\n")
            print("----------------------------------------------------------------")
            print("  What to do next:")
            print("  1. Check your email inbox (and spam/promotions folder).")
            print("  2. Look for the confirmation email: 'Claim your free access'")
            print("  3. Click the activation button inside to activate your")
            print("     12-Month Google AI Plus access.")
            print("----------------------------------------------------------------\n")
            return True
        elif redemption_url:
            try:
                from gui import save_result_file
                saved_path = save_result_file(
                    email=session_email,
                    password="(Existing Authenticated Session)",
                    name="Recovered Account",
                    phone="N/A",
                    url=redemption_url,
                )
                print(f"[+] Saved credentials and redemption link to: {saved_path}")
            except Exception:
                pass

            print("\n" + "=" * 64)
            print("  [SUCCESS] GOOGLE ONE REDEMPTION LINK ACQUIRED SUCCESSFULLY!")
            print("=" * 64)
            print(f"\nRedemption Link:\n{redemption_url}\n")
            return True
        else:
            print("\n[INFO] Please check your open browser tab to complete the final offer claim.")
            return False


if __name__ == "__main__":
    choice = sys.argv[1].lower().strip() if len(sys.argv) > 1 else None
    run_recovery(choice)
