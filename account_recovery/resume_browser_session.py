"""
Multi-Mode Account Recovery & Profile Completion Tool
=====================================================
Safety Net Tool: Resumes uncompleted Internshala accounts and auto-claims
the Google One 1-Year Gemini Plus promotion.

Supports:
1. Interactive Automated Browser (Playwright native launch - no port issues)
2. Instant Cookie Injection (Copies session from already-open browser)
3. CDP Connection (Attaches to existing port 9222 if active)
"""

import os
import sys
import time
import socket
from typing import Optional, List, Dict

# Resolve project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from playwright.sync_api import sync_playwright
from claimer import GeminiAIClaimer

CDP_PORT = 9222
PREFERENCES_URL = "https://internshala.com/student/preferences"
LOGIN_URL = "https://internshala.com/login/user"
PROMO_URL = "https://internshala.com/google-gemini-ai-plus"


def is_port_open(port: int = CDP_PORT, host: str = "127.0.0.1") -> bool:
    """Check if remote debugging port is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.8)
        return sock.connect_ex((host, port)) == 0


def parse_cookie_string(cookie_raw: str, domain: str = ".internshala.com") -> List[Dict]:
    """Parses a standard browser document.cookie string into Playwright cookie dicts."""
    cookies = []
    # Strip quotes if copied with quotes
    clean = cookie_raw.strip().strip('"').strip("'")
    for item in clean.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/"
            })
    return cookies


def run_pipeline_on_page(page, context) -> Optional[str]:
    """Runs preferences and claim pipeline on the target page."""
    claimer = GeminiAIClaimer(
        email="recovery@local",
        password="",
        mode="login",
        headless=False,
        allow_manual_verification=True,
    )

    print("\n-------------------------------------------------------")
    print("  STEP 1: AUTO-FILLING PREFERENCES")
    print("-------------------------------------------------------")
    # Check if we need to navigate to preferences
    if "preferences" not in page.url and "google-gemini-ai-plus" not in page.url:
        print(f"[*] Navigating to {PREFERENCES_URL}...")
        try:
            page.goto(PREFERENCES_URL, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[!] Navigation notice: {e}")

    page.wait_for_timeout(1000)
    success_pref = claimer._step_preferences(page)
    print(f"[Result] Preferences completion status: {success_pref}")

    if not success_pref:
        print("\n[ERROR] Preferences step could not be completed.")
        return None

    print("\n-------------------------------------------------------")
    print("  STEP 2: CLAIMING 12-MONTH FREE GEMINI PLUS PROMO LINK")
    print("-------------------------------------------------------")
    redemption_url = claimer._step_claim_gemini(page, context)
    if redemption_url:
        print("\n" + "=" * 68)
        print("  [SUCCESS] GOOGLE ONE REDEMPTION LINK ACQUIRED SUCCESSFULLY!")
        print("=" * 68)
        print(f"\nRedemption Link:\n{redemption_url}\n")

        # Save result locally
        results_dir = os.path.join(PROJECT_ROOT, "results")
        os.makedirs(results_dir, exist_ok=True)
        out_file = os.path.join(results_dir, f"recovered_{int(time.time())}.txt")
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(f"Google One 1-Year Access Offer Link:\n{redemption_url}\n")
            print(f"[OK] Link saved to: {out_file}")
        except Exception:
            pass
        return redemption_url
    else:
        print("\n[!] Could not automatically capture the final redemption link.")
        print("    Please check the open browser tab to complete the claim.")
        return None


def run_interactive_mode(email: str = "joybalboax2021@gmail.com", password: str = "joybalboax2021@gmail.com"):
    """
    Mode 1: Launches a visible browser directly via Playwright.
    Auto-fills credentials, allows user to solve captcha/verify if needed,
    then automatically takes over preferences and offer extraction.
    """
    print("\n" + "=" * 64)
    print("  MODE 1: INTERACTIVE AUTOMATED BROWSER")
    print("=" * 64)
    print("[*] Launching browser window...")

    with sync_playwright() as p:
        # Launch Google Chrome or fallback to Chromium
        try:
            browser = p.chromium.launch(channel="chrome", headless=False)
        except Exception:
            try:
                browser = p.chromium.launch(channel="msedge", headless=False)
            except Exception:
                browser = p.chromium.launch(headless=False)

        context = browser.new_context()
        page = context.new_page()

        print(f"[*] Navigating to {LOGIN_URL}...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Pre-fill credentials if login form is present
        try:
            email_field = page.locator("form#login_form input#email, input#email").first
            pwd_field = page.locator("form#login_form input#password, input#password").first
            if email_field.is_visible() and email:
                email_field.fill(email)
                print(f"[+] Filled account email: {email}")
            if pwd_field.is_visible() and password:
                pwd_field.fill(password)
                print("[+] Filled password.")
        except Exception:
            pass

        print("\n" + "-" * 60)
        print("  ACTION REQUIRED: COMPLETE LOGIN IN THE OPEN BROWSER WINDOW")
        print("  Click 'Login' or solve any security check if prompted.")
        print("  As soon as you are logged in, the automation takes over automatically!")
        print("-" * 60)

        # Wait until user is authenticated
        logged_in = False
        start_wait = time.time()
        while time.time() - start_wait < 120:
            curr_url = page.url
            if (
                "preferences" in curr_url
                or "personal_details" in curr_url
                or "dashboard" in curr_url
                or "google-gemini-ai-plus" in curr_url
                or page.locator(".profile_icon, .is_icon_header_profile, :has-text('Free Gemini Access')").first.is_visible()
            ):
                logged_in = True
                print("\n[+] Login detected! Automation taking over...")
                break
            page.wait_for_timeout(1000)

        if not logged_in:
            print("\n[!] Login wait timed out. Please run the script again when ready.")
            browser.close()
            return False

        # Run preferences and claim
        res = run_pipeline_on_page(page, context)
        print("\nKeeping browser open for 15 seconds to review...")
        page.wait_for_timeout(15000)
        browser.close()
        return bool(res)


def run_cookie_mode(cookie_input: str):
    """
    Mode 2: Injects session cookies into a clean Playwright instance.
    Directly accesses preferences without login or captcha.
    """
    print("\n" + "=" * 64)
    print("  MODE 2: INSTANT SESSION COOKIE INJECTION")
    print("=" * 64)

    cookies = parse_cookie_string(cookie_input)
    if not cookies:
        print("[ERROR] No valid cookies found in input.")
        return False

    print(f"[*] Parsed {len(cookies)} cookies. Launching browser with session...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False)
        except Exception:
            browser = p.chromium.launch(headless=False)

        context = browser.new_context()
        context.add_cookies(cookies)

        page = context.new_page()
        print(f"[*] Navigating directly to {PREFERENCES_URL} with authenticated cookies...")
        page.goto(PREFERENCES_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        res = run_pipeline_on_page(page, context)
        print("\nKeeping browser open for 15 seconds to review...")
        page.wait_for_timeout(15000)
        browser.close()
        return bool(res)


def run_cdp_mode():
    """Mode 3: Attaches over Chrome DevTools Protocol (CDP port 9222)."""
    print("\n" + "=" * 64)
    print("  MODE 3: ATTACH TO RUNNING BROWSER OVER CDP (Port 9222)")
    print("=" * 64)

    if not is_port_open(CDP_PORT):
        print(f"[ERROR] Port {CDP_PORT} is not listening.")
        print("Chrome must be launched with --remote-debugging-port=9222 --user-data-dir=... to use this mode.")
        return False

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        except Exception as e:
            print(f"[ERROR] Could not connect over CDP: {e}")
            return False

        context = browser.contexts[0]
        print(f"Connected! Inspecting {len(context.pages)} open tab(s)...")

        target_page = None
        for page in context.pages:
            if "internshala.com" in page.url:
                target_page = page
                print(f"Found active Internshala tab: {page.url}")
                break

        if not target_page:
            target_page = context.new_page()
            target_page.goto(PREFERENCES_URL, wait_until="domcontentloaded")

        target_page.bring_to_front()
        return bool(run_pipeline_on_page(target_page, context))


def main():
    print("=" * 68)
    print("  Internshala Safety Net: Profile Completer & Offer Claimer")
    print("=" * 68)
    print("\nChoose recovery method:")
    print("  [1] Interactive Automated Browser (Recommended - zero setup)")
    print("      Opens a browser window with your credentials, waits for login,")
    print("      then automatically auto-fills preferences and claims the promo.")
    print("\n  [2] Instant Cookie Injection (Fastest - bypasses login completely)")
    print("      Paste document.cookie from your already-open browser tab.")
    print("\n  [3] Attach to Debug Port 9222 (CDP)")
    print()

    choice = input("Enter choice [1-3] (Default 1): ").strip()
    if not choice:
        choice = "1"

    if choice == "1":
        email = input("Enter account email (Default joybalboax2021@gmail.com): ").strip()
        if not email:
            email = "joybalboax2021@gmail.com"
        pwd = input(f"Enter account password (Default {email}): ").strip()
        if not pwd:
            pwd = email
        run_interactive_mode(email, pwd)

    elif choice == "2":
        print("\nHow to get cookies from your open Internshala tab:")
        print("  1. In your open Chrome tab, press F12 (Developer Tools).")
        print("  2. Click the 'Console' tab.")
        print("  3. Type: document.cookie and press Enter.")
        print("  4. Right-click and copy the output string.")
        print()
        cookie_str = input("Paste cookie string here: ").strip()
        if cookie_str:
            run_cookie_mode(cookie_str)
        else:
            print("[!] No cookies provided.")

    elif choice == "3":
        run_cdp_mode()

    else:
        run_interactive_mode()


if __name__ == "__main__":
    main()
