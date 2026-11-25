"""
Google AI Plus (1-Year Free) Access Portal - Application Entry Point
Supports modern GUI interface and headless CLI execution.
Includes auto-environment resolution to ensure virtual environment dependencies are always used.
"""

import os
import sys
import subprocess
import ctypes

if sys.platform == "win32":
    try:
        myappid = "nmrisrl11.googleaiplus.claimerportal.v100"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Self-healing environment check: ensure running with .venv if available
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CURRENT_DIR, ".venv", "Scripts", "python.exe")
VENV_PYTHONW = os.path.join(CURRENT_DIR, ".venv", "Scripts", "pythonw.exe")

current_exe = os.path.normcase(sys.executable)
valid_exes = [os.path.normcase(VENV_PYTHON), os.path.normcase(VENV_PYTHONW)]

if os.path.exists(VENV_PYTHON) and current_exe not in valid_exes:
    target_exe = VENV_PYTHON if "--cli" in sys.argv else VENV_PYTHONW
    ret = subprocess.call([target_exe] + sys.argv)
    sys.exit(ret)

# Ensure customtkinter and pillow are available
try:
    import customtkinter
    from PIL import Image
except ImportError:
    print("[!] Setting up required visual packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(CURRENT_DIR, "requirements.txt")])
    import customtkinter
    from PIL import Image

import argparse
from app.ui.main_window import GeminiClaimerApp, save_result_file
from app.core.claimer import GeminiAIClaimer, generate_secure_password


def run_cli(args):
    print("=" * 68)
    print("   Google AI Plus (1-Year Access) Portal (CLI Mode)")
    print("=" * 68)

    email = args.email
    password = args.password or generate_secure_password(12)

    def on_request_otp(err_msg=None):
        if err_msg:
            print(f"\n[!] {err_msg}")
        return input("\n>>> Enter the 6-digit verification code sent to your email: ").strip()

    claimer = GeminiAIClaimer(
        email=email,
        password=password,
        mode=args.mode,
        first_name=args.first_name,
        last_name=args.last_name,
        phone_number=args.phone,
        headless=args.headless,
        manual_verification_timeout=args.manual_timeout,
        on_request_otp=on_request_otp,
    )

    url = claimer.run()
    if url:
        if url == "EMAIL_DISPATCHED":
            print("\n" + "=" * 68)
            print("[+] ACCOUNT SETUP COMPLETED SUCCESSFULLY!")
            print("=" * 68)
            print("\nYour profile has been fully completed and qualified.")
            print("The activation and redemption link has been sent directly")
            print("to your registered email address.\n")
            print("----------------------------------------------------------------")
            print("  What to do next:")
            print(f"  1. Check your email inbox: {email} (and spam/promotions folder).")
            print("  2. Look for the confirmation email: 'Claim your free access'")
            print("  3. Click the activation button inside to activate your")
            print("     12-Month Google AI Plus access.")
            print("----------------------------------------------------------------\n")
        else:
            print("\n" + "=" * 68)
            print("[+] REDEMPTION LINK READY:")
            print(f"    {url}")
            print("=" * 68)
            print("\n[*] How to activate:")
            print("   Open the offer link above in your browser and proceed with the activation directly on your screen.")
            print("   Follow the on-screen steps to complete your 1-Year Google AI Plus access.")
            print("\n[*] IMPORTANT NOTICE:")
            print("   Please carefully review all on-screen details, requirements, and prompts before confirming")
            print("   or proceeding with any steps on the destination page.\n")

        full_name = f"{args.first_name or ''} {args.last_name or ''}".strip() or "CLI User"
        try:
            saved_path = save_result_file(
                email=email,
                password=password,
                name=full_name,
                phone=args.phone or claimer.phone_number,
                url=url,
            )
            print(f"[+] Report saved to: {saved_path}\n")
        except Exception as e:
            print(f"[!] Could not save record file: {e}\n")
    else:
        print("\n[-] Process did not complete.")


def main():
    parser = argparse.ArgumentParser(description="Google AI Plus (1-Year Access) Portal")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode without GUI")
    parser.add_argument("--email", type=str, help="Your valid @gmail.com address (CLI mode)")
    parser.add_argument("--password", type=str, help="Account password (optional in CLI mode)")
    parser.add_argument("--mode", choices=["register", "login"], default="register", help="Mode: register or login")
    parser.add_argument("--first-name", type=str, help="First name (optional in CLI mode)")
    parser.add_argument("--last-name", type=str, help="Last name (optional in CLI mode)")
    parser.add_argument("--phone", type=str, help="10-digit Indian phone number (optional in CLI mode)")
    parser.add_argument("--headless", action="store_true", help="Run browser in background (headless)")
    parser.add_argument(
        "--manual-timeout",
        type=int,
        default=120,
        help="Timeout in seconds for manual verification in headed browser (default: 120)",
    )

    args = parser.parse_args()

    if args.cli:
        if not args.email:
            parser.error("--email is required when using --cli mode.")
        run_cli(args)
    else:
        app = GeminiClaimerApp()
        app.mainloop()


if __name__ == "__main__":
    main()
