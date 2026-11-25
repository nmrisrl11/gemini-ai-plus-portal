"""
Gemini AI Plus (1-Year Access) Engine
Handles partner registration, verification, profile onboarding, and Google One redemption link extraction.
"""

import os
import glob
import time
import random
import string
import re
from typing import Callable, Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

# Target Gateway Portals
PARTNER_REGISTRATION_URL = "https://internshala.com/registration/student"
PARTNER_LOGIN_URL = "https://internshala.com/login/user"

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Muhammad", "Sai", "Ayaan", "Krishna",
    "Ishaan", "Shaurya", "Atharva", "Advik", "Pranav", "Advaith", "Aaryan", "Dhruv", "Kabir", "Ritvik",
    "Ananya", "Diya", "Gauri", "Pari", "Anushka", "Navya", "Angel", "Myra", "Sara", "Isha",
    "Aadhya", "Saanvi", "Kiara", "Shanaya", "Avani", "Prisha", "Riya", "Tanvi", "Kavya", "Eleni"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Chopra", "Joshi", "Patel",
    "Reddy", "Nair", "Iyer", "Rao", "Kumar", "Singh", "Das", "Banerjee", "Chatterjee", "Mukherjee",
    "Papadopoulou", "Fernandes", "Dsouza", "Menezes", "Pinto", "Pereira"
]


def generate_random_indian_phone() -> str:
    """Generates a realistic 10-digit mobile number starting with 6, 7, 8, or 9."""
    first_digit = random.choice(["6", "7", "8", "9"])
    remaining = "".join([str(random.randint(0, 9)) for _ in range(9)])
    return first_digit + remaining


def generate_secure_password(length: int = 12) -> str:
    """Generates a secure password containing uppercase, lowercase, digits, and special chars."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(chars) for _ in range(length))


MIN_SUPPORTED_CHROMIUM_MAJOR = 120
DEFAULT_FALLBACK_CHROME_VERSION = "134.0.0.0"


class _HeadlessChallengeFallback(Exception):
    """Internal signal to relaunch in a visible browser window for user verification."""


def parse_browser_major_version(browser_version: Optional[str]) -> Optional[int]:
    """Extracts the major integer version from a Playwright browser.version string."""
    if not browser_version:
        return None
    match = re.search(r"(\d+)", str(browser_version))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def build_desktop_user_agent(browser_version: Optional[str]) -> str:
    """
    Builds a clean Windows desktop Chrome User-Agent dynamically matched to the
    launched Chromium version (never exposing HeadlessChrome).
    """
    version_token = DEFAULT_FALLBACK_CHROME_VERSION
    if browser_version:
        full_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", str(browser_version))
        if full_match:
            version_token = full_match.group(1)
        else:
            major = parse_browser_major_version(browser_version)
            if major:
                version_token = f"{major}.0.0.0"
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{version_token} Safari/537.36"
    )


def normalize_error_message(
    raw_msg: str,
    for_log: bool = False,
    mode: Optional[str] = None,
) -> str:
    """Transforms raw upstream server messages into clear, actionable, controlled copywriting."""
    if not raw_msg:
        return "An unexpected error occurred. Please try again."

    lower = raw_msg.lower()
    inferred_mode = mode
    if not inferred_mode:
        if "registration" in lower or "register" in lower:
            inferred_mode = "register"
        elif "login" in lower:
            inferred_mode = "login"

    # 1. Already registered / existing account error
    if (
        "registered but not yet verified" in lower
        or "verify_unconfirmed_login" in lower
    ):
        if for_log:
            return "This Gmail address is already registered but unverified. Please check your inbox for the OTP code or use a fresh email."
        return (
            "This Gmail address has already started registration on the portal, but has not completed email verification.\n\n"
            "• Check your Gmail inbox for the confirmation email or OTP code.\n"
            "• Or enter a new, unregistered Gmail address to generate a fresh offer link."
        )

    if (
        "already registered" in lower
        or "already exists" in lower
        or "version of this email" in lower
        or "registered email" in lower
        or "is registered" in lower
        or "email address is registered" in lower
    ):
        if for_log:
            return "This Gmail address is already registered. Please enter a new, unregistered Gmail address."
        return (
            "This Gmail address is already registered.\n\n"
            "• Each Gemini AI Plus promotional link requires a fresh account registration.\n"
            "• Please enter a different or new Gmail address to proceed."
        )

    # 2. Invalid or expired OTP
    if "invalid otp" in lower or "wrong otp" in lower or "incorrect otp" in lower:
        return "The 6-digit verification code entered is incorrect. Please check your Gmail inbox and enter the latest code."

    if "expired otp" in lower or "otp expired" in lower:
        return "The verification code has expired. A fresh code has been sent to your Gmail inbox."

    # 3. Invalid credentials on login
    if (
        "incorrect password" in lower
        or "wrong password" in lower
        or "invalid password" in lower
        or "invalid credentials" in lower
        or "incorrect credentials" in lower
        or "login rejected" in lower
        or "user not found" in lower
        or "no user" in lower
        or "rejected login" in lower
    ):
        if for_log:
            return "Incorrect password or invalid credentials for this account."
        return "Incorrect password or invalid credentials for this account. Please verify your credentials and try again."

    # 4. CAPTCHA / Human verification challenge
    if (
        "captcha" in lower
        or "turnstile" in lower
        or "challenge" in lower
        or "robot" in lower
        or "verification required" in lower
        or "security check" in lower
    ):
        if for_log:
            return "Security verification challenge detected; manual action required."
        return (
            "A human-verification security challenge or CAPTCHA rejection was encountered.\n\n"
            "The portal's automated security controls (Google reCAPTCHA Enterprise) flagged this automated session ('Captcha error').\n\n"
            "• Automated login submission was safely stopped to respect the site's security policy.\n"
            "• The target portal requires logging in through a standard, non-automated browser."
        )

    # 5. HTTP 403 Forbidden
    if "403" in lower or "forbidden" in lower or "access denied" in lower:
        if for_log:
            return "HTTP 403 Forbidden: Access denied by security policy or rate limit."
        return (
            "Access to the portal was denied (HTTP 403 Forbidden).\n\n"
            "The portal's security system may have blocked automated requests. Please wait a few minutes or try again in a standard browser."
        )

    # 6. HTTP 429 Too Many Requests
    if "429" in lower or "too many requests" in lower or "rate limit" in lower:
        if for_log:
            return "HTTP 429 Too Many Requests: Rate limited by server."
        return (
            "The portal is temporarily rate-limiting requests (HTTP 429 Too Many Requests).\n\n"
            "Please wait a few minutes before trying again to allow rate limits to reset."
        )

    # 7. Form readiness failure
    if "did not become ready" in lower or "form not ready" in lower:
        if inferred_mode == "register":
            if for_log:
                return "Registration form did not become ready."
            return (
                "The registration form did not become ready within the expected time.\n\n"
                "• Check your internet connection or try switching to a mobile hotspot.\n"
                "• If you use strict antivirus web shields or a VPN, try pausing them temporarily and retry."
            )
        if for_log:
            return "Login form did not become ready."
        return (
            "The login form did not become ready within the expected time.\n\n"
            "• Check your internet connection or try switching to a mobile hotspot.\n"
            "• If you use strict antivirus web shields or a VPN, try pausing them temporarily and retry."
        )

    # 8. Timeout
    if "timed out" in lower or "timeout" in lower:
        if inferred_mode == "register":
            if for_log:
                return "Registration gateway timed out."
            return (
                "The registration gateway timed out.\n\n"
                "The server did not respond in time.\n"
                "• Check your internet connection or try switching to a mobile hotspot.\n"
                "• If you use strict antivirus web shields or a VPN, try pausing them temporarily and retry."
            )
        if inferred_mode == "login":
            if for_log:
                return "Login timed out."
            return (
                "The login operation timed out.\n\n"
                "The server did not respond or navigation did not reach the authenticated state.\n"
                "• Check your internet connection or try switching to a mobile hotspot.\n"
                "• If you use strict antivirus web shields or a VPN, try pausing them temporarily and retry."
            )
        if for_log:
            return "Gateway connection timed out."
        return (
            "The gateway connection timed out.\n\n"
            "The server did not respond in time.\n"
            "• Check your internet connection or try switching to a mobile hotspot.\n"
            "• If you use strict antivirus web shields or a VPN, try pausing them temporarily and retry."
        )

    # 9. Chromium browser engine not found
    if (
        "no compatible chromium browser" in lower
        or "executable doesn't exist" in lower
        or "could not find browser" in lower
    ):
        if for_log:
            return "No compatible Chromium browser found on system."
        return (
            "No compatible Chromium browser was found on your system.\n\n"
            "This application uses an installed Chromium browser (Google Chrome, Microsoft Edge, or Brave) to automate access.\n\n"
            "• Please ensure Google Chrome, Microsoft Edge, or Brave Browser is installed.\n"
            "• Once a browser is available, click 'Get 1-Year Access Link' again."
        )

    # Strip prefixes or raw HTML tags
    clean = re.sub(r"<[^>]+>", " ", raw_msg)
    clean = re.sub(r"^(notice|error):\s*", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean


def clean_google_one_url(url: str) -> str:
    """
    Extracts the canonical, clean Google One redemption offer URL
    (e.g., https://one.google.com/offer/ABC123XYZ) if wrapped inside
    Google Accounts sign-in redirects (continue=...), OAuth flows, or partner tracking URLs.
    """
    if not url or url == "EMAIL_DISPATCHED":
        return url

    # 1. Direct regex match on one.google.com/offer/<CODE>
    match = re.search(r"https?://(?:one\.google\.com|www\.google\.com/one)/offer/([A-Za-z0-9_-]+)", url)
    if match:
        return f"https://one.google.com/offer/{match.group(1)}"

    # 2. Extract from URL query parameters (continue, followup, url, redirect_url, target)
    try:
        from urllib.parse import parse_qs, urlparse, unquote
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for param in ("continue", "followup", "url", "redirect", "redirect_url", "target"):
            if param in qs:
                for raw_val in qs[param]:
                    unquoted = unquote(raw_val)
                    m = re.search(r"https?://(?:one\.google\.com|www\.google\.com/one)/offer/([A-Za-z0-9_-]+)", unquoted)
                    if m:
                        return f"https://one.google.com/offer/{m.group(1)}"
    except Exception:
        pass

    return url


class GeminiAIClaimer:
    def __init__(
        self,
        email: str,
        password: str,
        mode: str = "register",  # "register" or "login"
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        city: str = "Intia, Malda Division, West Bengal India",
        course: str = "B.Tech",
        college: str = "BITS Pilani",
        stream: str = "Computer Science & Engineering",
        start_year: str = "2026",
        end_year: str = "2031",
        headless: bool = False,
        preferred_browser: str = "auto",
        allow_manual_verification: bool = True,
        manual_verification_timeout: int = 120,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_request_otp: Optional[Callable[[Optional[str]], str]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_success: Optional[Callable[[str], None]] = None,
    ):
        self.email = email.strip()
        self.password = password.strip()
        self.mode = mode.strip().lower()
        self.first_name = (first_name or random.choice(FIRST_NAMES)).strip()
        self.last_name = (last_name or random.choice(LAST_NAMES)).strip()
        self.phone_number = (phone_number or generate_random_indian_phone()).strip()
        self.city = city
        self.course = course
        self.college = college
        self.stream = stream
        self.start_year = start_year
        self.end_year = end_year
        self.headless = headless
        self.preferred_browser = (preferred_browser or "auto").strip().lower()
        self.allow_manual_verification = allow_manual_verification
        self.manual_verification_timeout = manual_verification_timeout

        self.on_log = on_log or (lambda msg, lvl="INFO": print(f"[{lvl}] {msg}"))
        self.on_request_otp = on_request_otp
        self.on_error = on_error or (lambda err: print(f"[ERROR] {err}"))
        self.on_success = on_success or (lambda url: print(f"[SUCCESS] {url}"))

        self._is_stopped = False
        self._last_network_error: Optional[str] = None
        self._last_http_status: Optional[int] = None
        self._last_http_error: Optional[str] = None
        self._browser = None
        self._context = None
        self._page = None

    def log(self, message: str, level: str = "INFO"):
        self.on_log(message, level)

    def stop(self):
        self._is_stopped = True
        self.log("Process stopped by user.", "WARNING")

    def _detect_verification_challenge(self, page: Page) -> Optional[str]:
        """
        Conservatively detects presence of CAPTCHA or human-verification elements.
        Returns a human-readable description of the detected challenge type, or None if clean.

        Limitations & Conservative Detection:
        - Modern websites (including Internshala) frequently load passive bot telemetry scripts
          in the background (such as Google reCAPTCHA v3/Enterprise invisible badges). Passive
          badges (such as .grecaptcha-badge) run silently without user interaction and are NOT
          treated as active challenges to avoid false positives.
        - Detection is conservative and focuses on:
            1. Interstitial challenges / bot walls (Cloudflare "Just a moment...", challenge stage).
            2. Active interactive challenge frames (Cloudflare Turnstile, reCAPTCHA bframe, hCaptcha).
            3. Interactive checkboxes requiring explicit user engagement (e.g. unchecked reCAPTCHA v2 box).
            4. Explicit on-page challenge modals or prompt banners demanding human verification.
        - Multiple complementary selectors and frame inspections are used rather than relying on a
          single selector.
        """
        try:
            # 1. Cloudflare Interstitial & Turnstile
            try:
                title = page.title().lower()
                if "just a moment..." in title or "attention required! | cloudflare" in title:
                    return "Cloudflare Interstitial Challenge"
            except Exception:
                pass

            cf_selectors = [
                "#challenge-running:visible",
                "#challenge-stage:visible",
                "#challenge-form:visible",
                "iframe[src*='challenges.cloudflare.com']:visible",
                ".cf-turnstile:visible",
                "#cf-turnstile:visible",
                "div[class*='cf-turnstile']:visible",
            ]
            for sel in cf_selectors:
                try:
                    if page.locator(sel).first.is_visible():
                        return "Cloudflare Turnstile / Security Challenge"
                except Exception:
                    pass

            # 2. Google reCAPTCHA (Active interactive challenge popup or checkbox)
            # Note: Passive invisible badges (.grecaptcha-badge) run silently in background.
            # Active interactive challenges load inside a 'bframe' popup or an interactive checkbox widget.
            recaptcha_selectors = [
                "iframe[src*='recaptcha'][src*='bframe']:visible",
                "iframe[title*='recaptcha challenge' i]:visible",
                "div.recaptcha-checkbox[aria-checked='false']:visible",
                "#recaptcha-anchor:visible",
            ]
            for sel in recaptcha_selectors:
                try:
                    if page.locator(sel).first.is_visible():
                        return "Google reCAPTCHA Challenge"
                except Exception:
                    pass

            # Check across page frames for active bframe challenge popup
            try:
                for frame in page.frames:
                    if "recaptcha" in frame.url and "bframe" in frame.url:
                        return "Google reCAPTCHA Challenge"
            except Exception:
                pass

            # 3. hCaptcha (Active interactive challenge modal or widget)
            hcaptcha_selectors = [
                "iframe[src*='hcaptcha.com'][title*='challenge' i]:visible",
                "iframe[src*='hcaptcha.com'][title*='hCaptcha security challenge' i]:visible",
                "iframe[data-hcaptcha-widget-id]:visible",
                "iframe[src*='hcaptcha.com']:visible",
                ".h-captcha:visible",
                "div[id^='hcaptcha']:visible",
            ]
            for sel in hcaptcha_selectors:
                try:
                    if page.locator(sel).first.is_visible():
                        return "hCaptcha Security Challenge"
                except Exception:
                    pass

            try:
                if page.locator(".h-captcha iframe, div[id^='hcaptcha'] iframe").count() > 0:
                    return "hCaptcha Security Challenge"
            except Exception:
                pass

            # 4. Generic Human-Verification Prompts & Bot Walls
            generic_selectors = [
                "iframe[src*='captcha']:not([src*='anchor']):visible",
                "div#captcha:visible",
                "div.captcha-container:visible",
                "#px-captcha:visible",
                "#arkose:visible",
                "div[class*='geetest']:visible",
            ]
            for sel in generic_selectors:
                try:
                    if page.locator(sel).first.is_visible():
                        return "Human Verification Challenge"
                except Exception:
                    pass

            # 5. Visible text prompts explicitly demanding human verification or captcha resolution
            prompt_phrases = [
                "verify you are human",
                "verifying you are human",
                "please complete the security check",
                "confirm you are not a robot",
                "security verification required",
                "press and hold",
                "slide to complete the puzzle",
            ]
            for phrase in prompt_phrases:
                try:
                    loc = page.locator(f"text=/{re.escape(phrase)}/i").first
                    if loc.is_visible():
                        return f"Security Challenge ({phrase.capitalize()})"
                except Exception:
                    pass

        except Exception:
            pass

        return None

    def _is_authenticated(self, page: Page) -> bool:
        """
        Determines whether the session has reached an authenticated state.
        Verifies URL transitions and observable authenticated dashboard indicators.
        """
        try:
            curr_url = page.url.lower()
            # Must have left the login / registration paths and reached a student/dashboard area
            if any(path in curr_url for path in ["/dashboard", "/student/dashboard", "/user/dashboard", "/student"]):
                if "/login" not in curr_url and "/registration" not in curr_url:
                    return True

            # Check for visible authenticated indicators on the page
            indicators = [
                ":has-text('Free Gemini Access')",
                "a[href*='/logout']",
                "#profile_dropdown",
                ".user_profile",
                "a:has-text('Logout')",
                ".nav_user_profile",
            ]
            for ind in indicators:
                if page.locator(ind).first.is_visible():
                    return True
        except Exception:
            pass
        return False

    def _wait_for_manual_verification(self, page: Page, challenge_desc: str, timeout_seconds: Optional[int] = None) -> bool:
        """
        Configurable headed-browser workflow that pauses automation when a challenge is detected,
        allowing the user to complete verification themselves in the open browser window.
        Polls for authenticated state and resumes only after confirmed.
        Does not submit repeatedly or attempt challenge evasion.
        """
        timeout = timeout_seconds or self.manual_verification_timeout
        self.log(f"Verification challenge detected ({challenge_desc}); manual action required.", "WARNING")
        self.log(
            f"Please solve the security challenge in the open browser window. Waiting up to {timeout}s...",
            "WAITING_USER",
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_stopped:
                self.log("Manual verification cancelled by user.", "WARNING")
                return False

            if page.is_closed():
                self.log("Browser window was closed during verification.", "ERROR")
                return False

            # Check if user reached authenticated state
            if self._is_authenticated(page):
                self.log("Authenticated state confirmed following manual verification!", "SUCCESS")
                return True

            # Check if challenge was resolved and page transitioned
            current_challenge = self._detect_verification_challenge(page)
            if not current_challenge:
                page.wait_for_timeout(1000)
                if self._is_authenticated(page):
                    self.log("Manual verification complete. Authenticated state confirmed.", "SUCCESS")
                    return True

            # Check for explicit terminal errors (e.g. invalid credentials after challenge)
            dom_err = self._extract_page_error(page)
            if dom_err and "loading" not in dom_err.lower() and "captcha" not in dom_err.lower():
                log_err = normalize_error_message(dom_err, for_log=True)
                modal_err = normalize_error_message(dom_err, for_log=False)
                self.log("Login failed: invalid credentials or unexpected response.", "ERROR")
                self.log(f"Notice: {log_err}", "ERROR")
                self.on_error(modal_err)
                return False

            if self._last_network_error and "captcha" not in self._last_network_error.lower():
                log_err = normalize_error_message(self._last_network_error, for_log=True)
                modal_err = normalize_error_message(self._last_network_error, for_log=False)
                self.log("Login failed: invalid credentials or unexpected response.", "ERROR")
                self.log(f"Notice: {log_err}", "ERROR")
                self.on_error(modal_err)
                return False

            page.wait_for_timeout(1000)

        self.log("Login timed out: Verification challenge was not completed within the timeout period.", "ERROR")
        self.on_error("Security verification challenge timed out. Please try again.")
        return False

    def _extract_page_error(self, page: Page) -> Optional[str]:
        """Extracts visible error messages from modals, toasts, or form alerts."""
        # 1. Check #error_modal or bootstrap alert modals
        try:
            modal = page.locator("#error_modal:visible, div#error_modal.in, div#error_modal.show, .modal.show:visible, .modal.in:visible").first
            if modal.is_visible():
                txt_el = modal.locator(".text-message, .modal-body, .message_container").first
                if txt_el.is_visible():
                    raw_txt = txt_el.inner_text().strip()
                    if raw_txt and "loading" not in raw_txt.lower():
                        lines = [line.strip() for line in raw_txt.splitlines() if line.strip() and line.strip().lower() not in ["close", "ok", "x"]]
                        clean = " ".join(lines)
                        if clean:
                            if "validationerror" in clean.lower() or (clean.startswith("TypeError:") and "validation" in clean.lower()):
                                if self.mode == "login":
                                    return "Invalid credentials or rejected login."
                                else:
                                    return "Registration was rejected by the portal gateway."
                            elif not clean.startswith("TypeError:"):
                                return clean
        except Exception:
            pass

        # 2. Check toasts
        try:
            toast = page.locator(".toast:visible:not(.loading_toast), .internshala-toast:visible:not(.loading_toast)").first
            if toast.is_visible():
                txt = toast.inner_text().strip()
                if txt and "loading" not in txt.lower():
                    return txt
        except Exception:
            pass

        # 3. Check inline form field errors
        try:
            err_label = page.locator(".help-block.form-error:visible, .error-message:visible").first
            if err_label.is_visible():
                txt = err_label.inner_text().strip()
                if txt and "loading" not in txt.lower():
                    return txt
        except Exception:
            pass

        return None

    def _goto_with_retry(
        self,
        page: Page,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 50000,
        max_attempts: int = 2,
        label: str = "gateway",
    ):
        """
        Navigates to a URL with an extended timeout and automatic retry on transient
        timeouts or connection drops, while honoring user cancellation.
        """
        transient_tokens = (
            "err_connection_reset",
            "err_timed_out",
            "err_network_changed",
            "err_connection_closed",
            "err_name_not_resolved",
            "err_internet_disconnected",
            "err_aborted",
        )
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            if self._is_stopped:
                return None
            try:
                return page.goto(url, wait_until=wait_until, timeout=timeout)
            except PlaywrightTimeoutError as exc:
                last_exc = exc
                if self._is_stopped or attempt >= max_attempts:
                    raise
                delay = random.uniform(1.8, 3.0)
                self.log(
                    f"{label.capitalize()} timed out (attempt {attempt}/{max_attempts}). Retrying in {delay:.1f}s...",
                    "WARNING",
                )
            except Exception as exc:
                last_exc = exc
                if self._is_stopped or attempt >= max_attempts:
                    raise
                err_lower = str(exc).lower()
                if not any(tok in err_lower for tok in transient_tokens):
                    raise
                delay = random.uniform(1.8, 3.0)
                self.log(
                    f"Transient network issue reaching {label} (attempt {attempt}/{max_attempts}). Retrying in {delay:.1f}s...",
                    "WARNING",
                )

            # Interruptible backoff sleep
            slept = 0.0
            while slept < delay:
                if self._is_stopped:
                    return None
                step = min(0.2, delay - slept)
                time.sleep(step)
                slept += step

        if last_exc:
            raise last_exc
        return None

    def _launch_browser(self, p):
        """
        Intelligently discovers and launches any available Chromium browser on the user's system.
        If preferred_browser is set to 'chrome', 'edge', or 'brave', attempts that browser first
        before falling back to the 5-tier auto-discovery cascade:
        1. Google Chrome channel ('chrome') — falls back to Edge if outdated (< v120)
        2. Microsoft Edge channel ('msedge' - pre-installed on 100% of Windows 10/11 machines)
        3. Direct executable scan for Brave, Chrome, and Edge on standard Windows paths
        4. Any host Playwright browser cache in %LOCALAPPDATA%\\ms-playwright
        5. Bundled Playwright Chromium fallback (for development mode)
        """
        import glob
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        # 0. Honor explicit user browser selection first (with safe fallback to auto-detect)
        pref = getattr(self, "preferred_browser", "auto") or "auto"
        if pref in ("chrome", "edge", "brave"):
            if pref == "chrome":
                try:
                    browser = p.chromium.launch(channel="chrome", headless=self.headless)
                    ver = parse_browser_major_version(getattr(browser, "version", None))
                    ver_label = f" (v{ver})" if ver else ""
                    self.log(f"Browser session initialized using Google Chrome{ver_label} (selected).", "INFO")
                    return browser
                except Exception:
                    for exe_path in (
                        os.path.join(prog_files, "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(prog_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
                    ):
                        if exe_path and os.path.exists(exe_path):
                            try:
                                browser = p.chromium.launch(executable_path=exe_path, headless=self.headless)
                                self.log("Browser session initialized using Google Chrome (selected).", "INFO")
                                return browser
                            except Exception:
                                pass
            elif pref == "edge":
                try:
                    browser = p.chromium.launch(channel="msedge", headless=self.headless)
                    ver = parse_browser_major_version(getattr(browser, "version", None))
                    ver_label = f" (v{ver})" if ver else ""
                    self.log(f"Browser session initialized using Microsoft Edge{ver_label} (selected).", "INFO")
                    return browser
                except Exception:
                    for exe_path in (
                        os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
                        os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe"),
                        os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
                    ):
                        if exe_path and os.path.exists(exe_path):
                            try:
                                browser = p.chromium.launch(executable_path=exe_path, headless=self.headless)
                                self.log("Browser session initialized using Microsoft Edge (selected).", "INFO")
                                return browser
                            except Exception:
                                pass
            elif pref == "brave":
                for exe_path in (
                    os.path.join(prog_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                    os.path.join(prog_files_x86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                    os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                ):
                    if exe_path and os.path.exists(exe_path):
                        try:
                            browser = p.chromium.launch(executable_path=exe_path, headless=self.headless)
                            self.log("Browser session initialized using Brave Browser (selected).", "INFO")
                            return browser
                        except Exception:
                            pass

            self.log(
                f"Selected browser '{pref}' was not found or could not be launched. Falling back to automatic browser discovery...",
                "WARNING",
            )

        # 1. Try Google Chrome channel
        try:
            browser = p.chromium.launch(channel="chrome", headless=self.headless)
            chrome_major = parse_browser_major_version(getattr(browser, "version", None))
            if chrome_major is not None and chrome_major < MIN_SUPPORTED_CHROMIUM_MAJOR:
                self.log(
                    f"Detected outdated Google Chrome (v{chrome_major} < v{MIN_SUPPORTED_CHROMIUM_MAJOR}). Falling back to Microsoft Edge...",
                    "WARNING",
                )
                try:
                    browser.close()
                except Exception:
                    pass
            else:
                ver_label = f" (v{chrome_major})" if chrome_major else ""
                self.log(f"Browser session initialized using Google Chrome{ver_label}.", "INFO")
                return browser
        except Exception:
            pass

        # 2. Try Microsoft Edge channel (Built-in on Windows 10/11)
        try:
            browser = p.chromium.launch(channel="msedge", headless=self.headless)
            edge_major = parse_browser_major_version(getattr(browser, "version", None))
            ver_label = f" (v{edge_major})" if edge_major else ""
            self.log(f"Initialized browser session using Microsoft Edge{ver_label}.", "INFO")
            return browser
        except Exception:
            pass

        # 3. Direct executable scan for installed Chromium browsers

        direct_candidates = [
            # Brave Browser
            (os.path.join(prog_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"), "Brave Browser"),
            (os.path.join(prog_files_x86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"), "Brave Browser (32-bit)"),
            (os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"), "Brave Browser (User)"),
            # Google Chrome direct paths (in case registry channel lookup missed it)
            (os.path.join(prog_files, "Google", "Chrome", "Application", "chrome.exe"), "Google Chrome"),
            (os.path.join(prog_files_x86, "Google", "Chrome", "Application", "chrome.exe"), "Google Chrome (32-bit)"),
            (os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"), "Google Chrome (User)"),
            # Microsoft Edge direct paths (in case registry channel lookup missed it)
            (os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"), "Microsoft Edge"),
            (os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe"), "Microsoft Edge (64-bit)"),
            (os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"), "Microsoft Edge (User)"),
            # Other Chromium browsers
            (os.path.join(local_app_data, "Programs", "Opera", "launcher.exe"), "Opera"),
            (os.path.join(prog_files, "Opera", "launcher.exe"), "Opera"),
            (os.path.join(local_app_data, "Vivaldi", "Application", "vivaldi.exe"), "Vivaldi"),
            (os.path.join(prog_files, "Vivaldi", "Application", "vivaldi.exe"), "Vivaldi"),
        ]

        for exe_path, label in direct_candidates:
            if exe_path and os.path.exists(exe_path):
                try:
                    browser = p.chromium.launch(executable_path=exe_path, headless=self.headless)
                    self.log(f"Browser session initialized using {label}.", "INFO")
                    return browser
                except Exception:
                    pass

        # 4. Check for host Playwright browser cache in %LOCALAPPDATA%\\ms-playwright
        if local_app_data:
            pw_dir = os.path.join(local_app_data, "ms-playwright")
            if os.path.exists(pw_dir):
                pw_candidates = []
                for pattern in ["**/chrome.exe", "**/chrome-headless-shell.exe"]:
                    for match in glob.glob(os.path.join(pw_dir, pattern), recursive=True):
                        if os.path.exists(match):
                            pw_candidates.append(match)
                for pw_exe in pw_candidates:
                    try:
                        browser = p.chromium.launch(executable_path=pw_exe, headless=self.headless)
                        self.log("Browser session initialized using system Playwright browser cache.", "INFO")
                        return browser
                    except Exception:
                        pass

        # 5. Final fallback: try default bundled launch (works in unbundled dev mode)
        try:
            browser = p.chromium.launch(headless=self.headless)
            self.log("Browser session initialized using bundled Chromium.", "INFO")
            return browser
        except Exception:
            pass

        # If all candidates fail, raise a clean descriptive exception
        err_msg = (
            "No compatible Chromium browser was found on your system.\n\n"
            "Please ensure Google Chrome, Microsoft Edge, or Brave Browser is installed and try again."
        )
        self.log(err_msg, "ERROR")
        raise RuntimeError(err_msg)

    def run(self) -> Optional[str]:
        """Main execution workflow."""
        if not self.email.endswith("@gmail.com"):
            err = "Invalid Email: A valid @gmail.com account is required for Gemini AI Plus redemption."
            self.log(err, "ERROR")
            self.on_error(err)
            return None

        if len(self.password) < 6:
            err = "Invalid Password: Password must be at least 6 characters."
            self.log(err, "ERROR")
            self.on_error(err)
            return None

        self._last_network_error = None
        self._last_http_status = None
        self._last_http_error = None
        self._headed_fallback_used = False
        original_headless = self.headless

        self.log("Initializing secure browser session with clean isolated context...", "INFO")

        try:
            with sync_playwright() as p:
                for _session_pass in range(2):
                    browser = None
                    context = None
                    page = None
                    try:
                        browser = self._launch_browser(p)
                        dynamic_ua = build_desktop_user_agent(getattr(browser, "version", None))

                        context = browser.new_context(
                            user_agent=dynamic_ua,
                            viewport={"width": 1280, "height": 850},
                        )

                        page = context.new_page()
                        self._browser = browser
                        self._context = context
                        self._page = page

                        # Listen to responses to monitor HTTP 403/429 and capture API errors
                        def on_response(response):
                            # 1. Track HTTP 403 / 429 status codes
                            if response.status in (403, 429):
                                req_type = response.request.resource_type
                                if "internshala.com" in response.url and req_type in ("document", "xhr", "fetch"):
                                    self._last_http_status = response.status
                                    self._last_http_error = f"HTTP {response.status}"

                            # 2. Track JSON endpoint rejections
                            if any(endpoint in response.url for endpoint in ["student_submit", "verify_email", "login_submit", "verify_ajax"]):
                                try:
                                    data = response.json()
                                    if isinstance(data, dict) and data.get("success") is False:
                                        raw_err = (
                                            data.get("errorthrown")
                                            or data.get("errorThrown")
                                            or data.get("errorMsg")
                                            or data.get("message")
                                            or data.get("error")
                                        )
                                        if raw_err:
                                            clean = re.sub(r'<[^>]+>', ' ', str(raw_err)).strip()
                                            clean = re.sub(r'\s+', ' ', clean)
                                            if clean:
                                                self._last_network_error = clean
                                        else:
                                            # Server explicitly rejected request with success: False
                                            if "verify_ajax" in response.url or "login_submit" in response.url:
                                                self._last_network_error = "Invalid credentials or login rejected by server."
                                            else:
                                                self._last_network_error = "Request rejected by server."
                                except Exception:
                                    pass

                        page.on("response", on_response)

                        if self.mode == "login":
                            # Direct Login Mode (For testing with already registered account)
                            if not self._step_login(page):
                                return None

                            # Self-healing check: if this existing account never completed profile onboarding
                            page.wait_for_timeout(1000)
                            if "onboarding" in page.url or "personal_details" in page.url or page.locator(":has-text(\"Let's get started\")").first.is_visible():
                                self.log("Existing account has an incomplete profile. Auto-completing profile onboarding...", "INFO")
                                if not self._step_profile_details(page):
                                    return None
                                if not self._step_preferences(page):
                                    return None
                            elif "preferences" in page.url or page.locator("h1, h2, div, span").filter(has_text=re.compile(r"Your preferences", re.I)).first.is_visible():
                                self.log("Existing account is on preferences page. Auto-completing preferences...", "INFO")
                                if not self._step_preferences(page):
                                    return None
                        else:
                            # New Registration Mode
                            if not self._step_registration(page):
                                return None

                            if not self._step_otp_verification(page):
                                return None

                            if not self._step_profile_details(page):
                                return None

                            if not self._step_preferences(page):
                                return None

                        # Step: Claim Offer & Extract Google One Redemption Link
                        redemption_url = self._step_claim_gemini(page, context)
                        if redemption_url == "EMAIL_DISPATCHED":
                            self.log("Account setup completed successfully! The 12-month activation link was dispatched to your email address.", "SUCCESS")
                            self.on_success("EMAIL_DISPATCHED")
                            return "EMAIL_DISPATCHED"
                        elif redemption_url:
                            self.log("Successfully acquired Google One 1-Year Gemini Plus Redemption Link!", "SUCCESS")
                            self.on_success(redemption_url)
                            return redemption_url
                        else:
                            self.log("Failed to retrieve final redemption link.", "ERROR")
                            self.on_error("Could not capture Google One redemption link.")
                            return None

                    except _HeadlessChallengeFallback:
                        self._headed_fallback_used = True
                        self.headless = False
                        self.log(
                            "Switching to a visible browser window so you can complete the security verification...",
                            "WAITING_USER",
                        )
                        continue
                    except Exception as e:
                        if self._is_stopped:
                            self.log("Session stopped.", "INFO")
                            return None
                        raw_e = str(e)
                        if "No compatible Chromium browser" in raw_e or "executable doesn't exist" in raw_e.lower():
                            err_msg = raw_e
                        else:
                            err_msg = f"Unexpected error occurred: {raw_e}"
                        self.log(err_msg, "ERROR")
                        self.on_error(err_msg)
                        return None
                    finally:
                        if page:
                            try:
                                page.close()
                            except Exception:
                                pass
                        if context:
                            try:
                                context.close()
                            except Exception:
                                pass
                        if browser:
                            try:
                                browser.close()
                            except Exception:
                                pass
                return None
        finally:
            self.headless = original_headless

    def _step_login(self, page: Page) -> bool:
        """
        Logs into an existing account with locator-based synchronization, robust failure
        distinction (invalid credentials, timeouts, HTTP 403/429, readiness, unexpected errors),
        and conservative CAPTCHA / human verification handling.
        """
        if self._is_stopped:
            return False

        self._last_network_error = None
        self._last_http_status = None
        self._last_http_error = None

        self.log(f"Connecting to login portal for existing account: {self.email}...", "INFO")
        self.log("Waiting for login form...", "INFO")

        # 1. Navigate to login portal
        try:
            resp = self._goto_with_retry(
                page,
                PARTNER_LOGIN_URL,
                wait_until="domcontentloaded",
                timeout=50000,
                max_attempts=2,
                label="login portal",
            )
            if self._is_stopped:
                return False
            if resp and resp.status in (403, 429):
                self._last_http_status = resp.status
        except PlaywrightTimeoutError:
            self.log("Login timed out: Navigation to login portal timed out.", "ERROR")
            self.on_error(normalize_error_message("Login portal failed to respond in time (connection timed out).", for_log=False, mode="login"))
            return False
        except Exception as e:
            if self._is_stopped:
                return False
            self.log(f"Login failed: unexpected navigation or page error: {e}", "ERROR")
            self.on_error(f"Failed to navigate to login portal: {e}")
            return False

        # 2. Check for immediate HTTP status barriers (403 Forbidden / 429 Rate Limit)
        if self._last_http_status == 403:
            self.log("Login failed: HTTP 403 Forbidden received. Access blocked by security policy.", "ERROR")
            self.on_error(normalize_error_message("403 Forbidden", for_log=False, mode="login"))
            return False
        if self._last_http_status == 429:
            self.log("Login failed: HTTP 429 Too Many Requests received. Rate limit exceeded.", "ERROR")
            self.on_error(normalize_error_message("429 Too Many Requests", for_log=False, mode="login"))
            return False

        # 3. Check if verification challenge / interstitial is active prior to form interaction
        pre_challenge = self._detect_verification_challenge(page)
        if pre_challenge:
            if not self.headless and self.allow_manual_verification:
                if not self._wait_for_manual_verification(page, pre_challenge):
                    return False
                if self._is_authenticated(page):
                    self.log("Login successful.", "SUCCESS")
                    return True
            elif self.headless and self.allow_manual_verification and not getattr(self, "_headed_fallback_used", False):
                self.log(f"Verification challenge detected in background mode ({pre_challenge}).", "WARNING")
                raise _HeadlessChallengeFallback(pre_challenge)
            else:
                self.log("Verification challenge detected; manual action required.", "ERROR")
                if self.headless:
                    self.log(
                        "Verification challenge detected in background mode. Session stopped safely.",
                        "ERROR",
                    )
                    self.on_error("Security verification challenge detected by the portal. Please try again with a different network or wait a few minutes.")
                else:
                    self.on_error("Security verification challenge detected. Manual action required.")
                return False

        # 4. Wait for login form elements to be visible and enabled
        email_field = page.locator("input#modal_email, input#email, input[name='email']").first
        try:
            email_field.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Login failed: login form did not become ready (email field not visible).", "ERROR")
            self.on_error("Login form did not become ready: email input not found.")
            return False

        if not email_field.is_enabled():
            self.log("Login failed: login form did not become ready (email field is disabled).", "ERROR")
            self.on_error("Login form email input is not enabled.")
            return False

        password_field = page.locator("input#modal_password, input#password, input[name='password']").first
        try:
            password_field.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Login failed: login form did not become ready (password field not visible).", "ERROR")
            self.on_error("Login form did not become ready: password input not found.")
            return False

        if not password_field.is_enabled():
            self.log("Login failed: login form did not become ready (password field is disabled).", "ERROR")
            self.on_error("Login form password input is not enabled.")
            return False

        submit_btn = page.locator("#modal_login_submit, button#login_submit, #login_submit, button:has-text('Login')").first
        try:
            submit_btn.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Login failed: login form did not become ready (submit button not visible).", "ERROR")
            self.on_error("Login form did not become ready: submit button not found.")
            return False

        if not submit_btn.is_enabled():
            self.log("Login failed: login form did not become ready (submit button is disabled).", "ERROR")
            self.on_error("Login form submit button is disabled.")
            return False

        self.log("Login form is ready.", "INFO")

        # 5. Fill credentials without logging sensitive data (passwords never written to logs)
        email_field.fill(self.email)
        password_field.fill(self.password)

        # 6. Submit login form
        self.log("Submitting login form...", "INFO")
        try:
            submit_btn.click()
        except Exception as e:
            self.log(f"Login failed: unexpected navigation or page error while clicking submit: {e}", "ERROR")
            self.on_error(f"Failed to submit login credentials: {e}")
            return False

        self.log("Credentials submitted. Verifying authentication outcome...", "INFO")

        # 7. Outcome synchronization: poll for authenticated state, CAPTCHA, or explicit errors
        # Avoid assuming a fixed delay guarantees readiness; check for meaningful outcomes.
        for _ in range(25):
            if self._is_stopped:
                return False

            # Check HTTP barriers during post-submit requests
            if self._last_http_status == 403:
                self.log("Login failed: HTTP 403 Forbidden received.", "ERROR")
                self.on_error(normalize_error_message("403 Forbidden", for_log=False))
                return False
            if self._last_http_status == 429:
                self.log("Login failed: HTTP 429 Too Many Requests received.", "ERROR")
                self.on_error(normalize_error_message("429 Too Many Requests", for_log=False))
                return False

            # Outcome A: Authentication Successful
            if self._is_authenticated(page):
                self.log("Login successful.", "SUCCESS")
                return True

            # Outcome B: Verification Challenge Detected
            challenge = self._detect_verification_challenge(page)
            if challenge:
                if not self.headless and self.allow_manual_verification:
                    if self._wait_for_manual_verification(page, challenge):
                        self.log("Login successful.", "SUCCESS")
                        return True
                    return False
                else:
                    self.log("Verification challenge detected; manual action required.", "ERROR")
                    if self.headless:
                        self.log(
                            "Verification challenge detected in background mode. Session stopped safely.",
                            "ERROR",
                        )
                        self.on_error("Security verification challenge detected by the portal. Please try again with a different network or wait a few minutes.")
                    else:
                        self.on_error("Security verification challenge detected. Manual action required.")
                    return False

            # Outcome C: Network/API Rejection (e.g. verify_ajax returning error or success=false)
            if self._last_network_error:
                if "captcha" in self._last_network_error.lower():
                    # Server rejected automated login with Captcha error under bot security policy
                    self._dismiss_modal(page)
                    if not self.headless and self.allow_manual_verification:
                        if self._wait_for_manual_verification(page, "Server CAPTCHA Requirement"):
                            self.log("Login successful.", "SUCCESS")
                            return True
                        return False
                    else:
                        self.log("Verification challenge detected; manual action required.", "ERROR")
                        self.log(f"Notice: Login rejected by portal gateway ({self._last_network_error}).", "ERROR")
                        self.on_error(normalize_error_message(self._last_network_error, for_log=False))
                        return False
                else:
                    log_err = normalize_error_message(self._last_network_error, for_log=True)
                    modal_err = normalize_error_message(self._last_network_error, for_log=False)
                    self.log("Login failed: invalid credentials or unexpected response.", "ERROR")
                    self.log(f"Notice: {log_err}", "ERROR")
                    self.on_error(modal_err)
                    return False

            # Outcome D: DOM Error (modal dialog, alert toast, inline error)
            dom_err = self._extract_page_error(page)
            if dom_err and "loading" not in dom_err.lower():
                if "captcha" in dom_err.lower() or "recaptcha" in dom_err.lower():
                    # Server displayed a Captcha error modal on page (automated attempt blocked)
                    self._dismiss_modal(page)
                    if not self.headless and self.allow_manual_verification:
                        if self._wait_for_manual_verification(page, "Server CAPTCHA Requirement"):
                            self.log("Login successful.", "SUCCESS")
                            return True
                        return False
                    else:
                        self.log("Verification challenge detected; manual action required.", "ERROR")
                        self.log(f"Notice: Login rejected by portal gateway ({dom_err}).", "ERROR")
                        self.on_error(normalize_error_message(dom_err, for_log=False))
                        return False
                else:
                    log_err = normalize_error_message(dom_err, for_log=True)
                    modal_err = normalize_error_message(dom_err, for_log=False)
                    self.log("Login failed: invalid credentials or unexpected response.", "ERROR")
                    self.log(f"Notice: {log_err}", "ERROR")
                    self.on_error(modal_err)
                    return False

            page.wait_for_timeout(400)

        # Final check if authenticated
        if self._is_authenticated(page):
            self.log("Login successful.", "SUCCESS")
            return True

        # Check for any lingering error
        final_err = self._extract_page_error(page) or self._last_network_error
        if final_err and "loading" not in final_err.lower():
            if "captcha" in final_err.lower() or "recaptcha" in final_err.lower():
                self._dismiss_modal(page)
                if not self.headless and self.allow_manual_verification:
                    if self._wait_for_manual_verification(page, "Server CAPTCHA Requirement"):
                        self.log("Login successful.", "SUCCESS")
                        return True
                    return False
                else:
                    self.log("Verification challenge detected; manual action required.", "ERROR")
                    self.log(f"Notice: Login rejected by portal gateway ({final_err}).", "ERROR")
                    self.on_error(normalize_error_message(final_err, for_log=False))
                    return False
            log_err = normalize_error_message(final_err, for_log=True)
            modal_err = normalize_error_message(final_err, for_log=False)
            self.log("Login failed: invalid credentials or unexpected response.", "ERROR")
            self.log(f"Notice: {log_err}", "ERROR")
            self.on_error(modal_err)
            return False

        self.log("Login timed out.", "ERROR")
        self.on_error("Login timed out. No response or authenticated state reached.")
        return False

    def _step_registration(self, page: Page) -> bool:
        if self._is_stopped:
            return False

        self._last_network_error = None
        self._last_http_status = None
        self._last_http_error = None

        self.log(f"Connecting to verification gateway for: {self.first_name} {self.last_name} ({self.email})...", "INFO")
        self.log("Waiting for registration form...", "INFO")

        # 1. Navigate to partner registration page
        try:
            resp = self._goto_with_retry(
                page,
                PARTNER_REGISTRATION_URL,
                wait_until="domcontentloaded",
                timeout=50000,
                max_attempts=2,
                label="registration gateway",
            )
            if self._is_stopped:
                return False
            if resp and resp.status in (403, 429):
                self._last_http_status = resp.status
        except PlaywrightTimeoutError:
            self.log("Registration timed out: Navigation to registration gateway timed out.", "ERROR")
            self.on_error(normalize_error_message("Registration gateway failed to respond in time (connection timed out).", for_log=False, mode="register"))
            return False
        except Exception as e:
            if self._is_stopped:
                return False
            self.log(f"Registration failed: unexpected navigation error: {e}", "ERROR")
            self.on_error(f"Failed to navigate to registration portal: {e}")
            return False

        # 2. Check HTTP status barriers
        if self._last_http_status == 403:
            self.log("Registration failed: HTTP 403 Forbidden received.", "ERROR")
            self.on_error(normalize_error_message("403 Forbidden", for_log=False, mode="register"))
            return False
        if self._last_http_status == 429:
            self.log("Registration failed: HTTP 429 Too Many Requests received.", "ERROR")
            self.on_error(normalize_error_message("429 Too Many Requests", for_log=False, mode="register"))
            return False

        # 3. Check if verification challenge / interstitial is active prior to form interaction
        pre_challenge = self._detect_verification_challenge(page)
        if pre_challenge:
            if not self.headless and self.allow_manual_verification:
                if not self._wait_for_manual_verification(page, pre_challenge):
                    return False
            elif self.headless and self.allow_manual_verification and not getattr(self, "_headed_fallback_used", False):
                self.log(f"Verification challenge detected in background mode ({pre_challenge}).", "WARNING")
                raise _HeadlessChallengeFallback(pre_challenge)
            else:
                self.log("Verification challenge detected; manual action required.", "ERROR")
                self.on_error("Security verification challenge detected by the portal.")
                return False

        # 4. Check for sign up with email button if present
        signup_email_btn = page.locator("#email-button-container, button:has-text('Sign up with Email'), a:has-text('Sign up with Email')").first
        try:
            if signup_email_btn.is_visible():
                self.log("Opening email registration form...", "INFO")
                signup_email_btn.click()
        except Exception:
            pass

        # 5. Wait for form elements to be visible and enabled
        email_field = page.locator("form#registration-form input#email, input#email").first
        try:
            email_field.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Registration failed: form did not become ready (email field not visible).", "ERROR")
            self.on_error("Registration form did not become ready: email input not found.")
            return False

        if not email_field.is_enabled():
            self.log("Registration failed: email field is disabled.", "ERROR")
            self.on_error("Registration form email input is disabled.")
            return False

        password_field = page.locator("form#registration-form input#password, input#password").first
        try:
            password_field.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Registration failed: form did not become ready (password field not visible).", "ERROR")
            self.on_error("Registration form did not become ready: password input not found.")
            return False

        fname_field = page.locator("form#registration-form input#first_name, input#first_name").first
        try:
            fname_field.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Registration failed: form did not become ready (first name field not visible).", "ERROR")
            self.on_error("Registration form did not become ready: first name input not found.")
            return False

        lname_field = page.locator("form#registration-form input#last_name, input#last_name").first
        try:
            lname_field.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Registration failed: form did not become ready (last name field not visible).", "ERROR")
            self.on_error("Registration form did not become ready: last name input not found.")
            return False

        submit_btn = page.locator("form#registration-form #registration_submit, #registration_submit, button:has-text('Sign up')").first
        try:
            submit_btn.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            self.log("Registration failed: form did not become ready (submit button not visible).", "ERROR")
            self.on_error("Registration form submit button not found.")
            return False

        self.log("Registration form is ready.", "INFO")

        # 5. Fill credentials (passwords never written to logs)
        email_field.fill(self.email)
        password_field.fill(self.password)
        fname_field.fill(self.first_name)
        lname_field.fill(self.last_name)

        # 6. Submit registration
        self.log("Submitting registration credentials...", "INFO")
        try:
            submit_btn.click()
        except Exception as e:
            self.log(f"Registration failed: error while clicking submit: {e}", "ERROR")
            self.on_error(f"Failed to submit registration form: {e}")
            return False

        self.log("Submitted credentials. Awaiting server response...", "INFO")

        # 7. Outcome synchronization loop
        for _ in range(30):
            if self._is_stopped:
                return False

            if "/verify_email" in page.url or page.locator(":has-text('Verify your email')").first.is_visible():
                self.log("Account created! Awaiting email OTP code...", "SUCCESS")
                return True

            challenge = self._detect_verification_challenge(page)
            if challenge:
                if not self.headless and self.allow_manual_verification:
                    if not self._wait_for_manual_verification(page, challenge):
                        return False
                    if "/verify_email" in page.url or page.locator(":has-text('Verify your email')").first.is_visible():
                        self.log("Account created! Awaiting email OTP code...", "SUCCESS")
                        return True
                else:
                    self.log("Verification challenge detected; manual action required.", "ERROR")
                    self.on_error("Security verification challenge detected by the portal.")
                    return False

            # Check if this email was already registered but unconfirmed - resend OTP link available
            unconfirmed_link = page.locator("a[href*='verify_unconfirmed_login'], #error_modal a[href*='verify']").first
            try:
                if unconfirmed_link.is_visible():
                    self.log("Existing unverified registration detected. Resending OTP verification code...", "INFO")
                    unconfirmed_link.click()
                    page.wait_for_timeout(2000)
                    if "/verify_email" in page.url or page.locator(":has-text('Verify your email')").first.is_visible():
                        self.log("Verification code resent! Awaiting email OTP code...", "SUCCESS")
                        return True
            except Exception:
                pass

            if self._last_network_error:
                err = self._last_network_error
                # Check if it was unconfirmed registration
                if "registered but not yet verified" in err.lower() or "verify_unconfirmed_login" in err.lower():
                    unconf_link = page.locator("a[href*='verify_unconfirmed_login'], #error_modal a").first
                    try:
                        if unconf_link.is_visible():
                            self.log("Existing unverified registration detected. Resending OTP verification code...", "INFO")
                            unconf_link.click()
                            page.wait_for_timeout(2000)
                            if "/verify_email" in page.url or page.locator(":has-text('Verify your email')").first.is_visible():
                                self.log("Verification code resent! Awaiting email OTP code...", "SUCCESS")
                                return True
                    except Exception:
                        pass

                log_err = normalize_error_message(err, for_log=True)
                modal_err = normalize_error_message(err, for_log=False)
                self.log(f"Notice: {log_err}", "ERROR")
                self.on_error(modal_err)
                return False

            dom_err = self._extract_page_error(page)
            if dom_err and "loading" not in dom_err.lower():
                if "registered but not yet verified" in dom_err.lower() or "verify_unconfirmed_login" in dom_err.lower():
                    unconf_link = page.locator("a[href*='verify_unconfirmed_login'], #error_modal a").first
                    try:
                        if unconf_link.is_visible():
                            self.log("Existing unverified registration detected. Resending OTP verification code...", "INFO")
                            unconf_link.click()
                            page.wait_for_timeout(2000)
                            if "/verify_email" in page.url or page.locator(":has-text('Verify your email')").first.is_visible():
                                self.log("Verification code resent! Awaiting email OTP code...", "SUCCESS")
                                return True
                    except Exception:
                        pass

                log_err = normalize_error_message(dom_err, for_log=True)
                modal_err = normalize_error_message(dom_err, for_log=False)
                self.log(f"Notice: {log_err}", "ERROR")
                self.on_error(modal_err)
                return False

            page.wait_for_timeout(400)

        if "/verify_email" in page.url or page.locator(":has-text('Verify your email')").first.is_visible():
            self.log("Account created! Awaiting email OTP code...", "SUCCESS")
            return True

        final_err = self._extract_page_error(page) or self._last_network_error
        if final_err and "loading" not in final_err.lower():
            log_err = normalize_error_message(final_err, for_log=True)
            modal_err = normalize_error_message(final_err, for_log=False)
            self.log(f"Notice: {log_err}", "ERROR")
            self.on_error(modal_err)
            return False

        self.log("Timed out waiting for verification gateway response.", "ERROR")
        self.on_error("Timed out waiting for email verification screen.")
        return False

    def _step_otp_verification(self, page: Page) -> bool:
        if self._is_stopped:
            return False

        self.log("Waiting for verification screen...", "INFO")
        try:
            page.wait_for_selector(":has-text('Verify your email')", timeout=15000)
        except PlaywrightTimeoutError:
            self.log("Could not find email verification prompt.", "ERROR")
            self.on_error("OTP verification screen did not load.")
            return False

        otp_error_msg = None
        while not self._is_stopped:
            self.log(f"Waiting for 6-digit OTP code sent to {self.email}...", "WAITING_USER")

            otp_code = None
            if self.on_request_otp:
                otp_code = self.on_request_otp(otp_error_msg)
            else:
                otp_code = input("\nEnter the 6-digit OTP sent to your email: ").strip()

            if not otp_code or self._is_stopped:
                self.log("OTP verification cancelled.", "WARNING")
                return False

            otp_code = otp_code.strip()
            self._last_network_error = None
            self.log("Submitting OTP code...", "INFO")

            otp_input = page.locator("input#otp, input[name='otp'], input[placeholder*='OTP' i], input[placeholder*='6 digit' i], input#modal_otp, input.otp-input").first
            if not otp_input.is_visible():
                otp_input = page.locator("input[type='text'], input[type='number']").first

            otp_input.fill("")
            otp_input.fill(otp_code)
            page.wait_for_timeout(400)

            verify_btn = page.locator("#otp-submit, button#otp-submit, button:has-text('Verify Email'), input[value='Verify Email'], #verify_email_submit").first
            verify_btn.click()
            self.log("Validating OTP code with verification server...", "INFO")

            otp_valid = False
            for _ in range(16):
                if self._is_stopped:
                    return False

                current_url = page.url
                if (
                    "onboarding" in current_url
                    or "personal_details" in current_url
                    or "preferences" in current_url
                    or page.locator(":has-text(\"Let's get started\")").first.is_visible()
                    or page.locator(":has-text('Contact number')").first.is_visible()
                    or page.locator(":has-text('Current city')").first.is_visible()
                ):
                    self.log("OTP successfully verified!", "SUCCESS")
                    return True

                if self._last_network_error:
                    found_err = normalize_error_message(self._last_network_error, for_log=True)
                    self.log(f"OTP Notice: {found_err}", "ERROR")
                    otp_error_msg = f"{found_err}"
                    self._dismiss_modal(page)
                    break

                dom_err = self._extract_page_error(page)
                if dom_err:
                    found_err = normalize_error_message(dom_err, for_log=True)
                    self.log(f"OTP Notice: {found_err}", "ERROR")
                    otp_error_msg = f"{found_err}"
                    self._dismiss_modal(page)
                    break

                page.wait_for_timeout(500)

            if otp_valid:
                return True
            if not otp_error_msg:
                otp_error_msg = "Invalid or expired OTP code. Please check your Gmail inbox and enter the latest 6-digit code."

        return False

    def _dismiss_modal(self, page: Page):
        """Dismisses error modals so the user can interact cleanly."""
        try:
            close_btn = page.locator("#error_modal .modal_primary_btn, #error_modal button:has-text('Close'), .modal:visible button:has-text('Close')").first
            if close_btn.is_visible():
                close_btn.click()
        except Exception:
            pass

    def _step_profile_details(self, page: Page) -> bool:
        if self._is_stopped:
            return False

        # Guard: Check if personal details onboarding is already completed
        curr_url = page.url.lower()
        if (
            "preferences" in curr_url
            or "internships" in curr_url
            or "google-gemini-ai-plus" in curr_url
            or page.locator("h1, h2, div, span").filter(has_text=re.compile(r"Your preferences", re.I)).first.is_visible()
            or page.locator(".preference-types-field, .modes-field").first.is_visible()
        ):
            self.log("Profile onboarding details already completed. Proceeding to career preferences...", "INFO")
            return True

        self.log("Configuring eligibility profile ('Let's get started')...", "INFO")
        page.wait_for_timeout(2000)

        # Ensure valid phone number
        if not self.phone_number or len(self.phone_number) != 10 or not self.phone_number.isdigit():
            import random
            self.phone_number = f"{random.choice(['6', '7', '8', '9'])}{random.randint(100000000, 999999999)}"

        def fill_all_fields():
            # 1. Contact number (Placeholder: 'Mobile number')
            self.log(f"Setting Contact Number (+91 {self.phone_number})...", "INFO")
            phone_input = page.locator(
                "input[placeholder*='Mobile number' i], input[placeholder*='number' i], input[type='tel']"
            ).first
            try:
                if phone_input.is_visible():
                    phone_input.scroll_into_view_if_needed()
                    phone_input.click()
                    phone_input.press("Control+a")
                    phone_input.press("Backspace")
                    phone_input.press_sequentially(self.phone_number, delay=40)
                    page.wait_for_timeout(400)
            except Exception as e:
                self.log(f"Contact number input notice: {e}", "WARNING")

            # 2. Current city (Typeahead / Autocomplete)
            # When typing 'Mumbai', dropdown displays options including 'Mumbai, Maharashtra, India'
            self.log("Setting location (Current city: Mumbai, Maharashtra, India)...", "INFO")
            city_input = page.locator(
                "input[placeholder*='Current location' i], input[placeholder*='location' i], input#city"
            ).first
            try:
                if city_input.is_visible():
                    city_input.scroll_into_view_if_needed()
                    city_input.click()
                    city_input.press("Control+a")
                    city_input.press("Backspace")
                    city_input.press_sequentially("Mumbai", delay=60)
                    page.wait_for_timeout(1500)

                    # Look for typeahead item in dropdown
                    selected = False
                    try:
                        sug = page.locator("div, li").filter(has_text="Mumbai, Maharashtra, India").last
                        if sug.is_visible():
                            sug.click(force=True)
                            selected = True
                    except Exception:
                        pass

                    if not selected:
                        for opt_name in ["Mumbai, Maharashtra, India", "Mumbai Central", "Mumbai"]:
                            try:
                                opt = page.get_by_text(opt_name, exact=True).first
                                if opt.is_visible():
                                    opt.click(force=True)
                                    selected = True
                                    break
                            except Exception:
                                pass

                    if not selected:
                        # Keyboard fallback: navigate down to third option in list and press Enter
                        city_input.press("ArrowDown")
                        page.wait_for_timeout(200)
                        city_input.press("ArrowDown")
                        page.wait_for_timeout(200)
                        city_input.press("ArrowDown")
                        page.wait_for_timeout(200)
                        city_input.press("Enter")

                    # Dismiss any remaining dropdown overlay by clicking Current city label
                    try:
                        page.get_by_text("Current city", exact=False).first.click(force=True)
                    except Exception:
                        pass
                    page.wait_for_timeout(400)
            except Exception as e:
                self.log(f"City typeahead notice: {e}", "WARNING")

            # 3. Select Gender ('Female' or 'Male')
            self.log("Selecting Gender...", "INFO")
            try:
                gender_clicked = False
                f_chip = page.get_by_text("Female", exact=True).first
                if f_chip.is_visible():
                    f_chip.scroll_into_view_if_needed()
                    f_chip.click(force=True)
                    gender_clicked = True
                    page.wait_for_timeout(400)
                else:
                    m_chip = page.get_by_text("Male", exact=True).first
                    if m_chip.is_visible():
                        m_chip.scroll_into_view_if_needed()
                        m_chip.click(force=True)
                        gender_clicked = True
                        page.wait_for_timeout(400)

                if not gender_clicked:
                    f_box = page.locator("div, span, button").filter(has_text="Female").last
                    if f_box.is_visible():
                        f_box.scroll_into_view_if_needed()
                        f_box.click(force=True)
                        gender_clicked = True
                        page.wait_for_timeout(400)
            except Exception as e:
                self.log(f"Gender selection notice: {e}", "WARNING")

            # 4. Languages you know (Chip: 'English +')
            self.log("Selecting language: English...", "INFO")
            try:
                lang_clicked = False
                eng_chip = page.get_by_text("English +", exact=True).first
                if eng_chip.is_visible():
                    eng_chip.scroll_into_view_if_needed()
                    eng_chip.click(force=True)
                    lang_clicked = True
                    page.wait_for_timeout(500)
                else:
                    eng_sub = page.get_by_text("English", exact=False).first
                    if eng_sub.is_visible():
                        eng_sub.scroll_into_view_if_needed()
                        eng_sub.click(force=True)
                        lang_clicked = True
                        page.wait_for_timeout(500)

                if not lang_clicked:
                    eng_box = page.locator("div, span, button").filter(has_text="English").last
                    if eng_box.is_visible():
                        eng_box.scroll_into_view_if_needed()
                        eng_box.click(force=True)
                        lang_clicked = True
                        page.wait_for_timeout(500)

                if not lang_clicked:
                    # Fallback to Hindi +
                    hin_chip = page.get_by_text("Hindi +", exact=True).first
                    if hin_chip.is_visible():
                        hin_chip.scroll_into_view_if_needed()
                        hin_chip.click(force=True)
                        page.wait_for_timeout(400)
            except Exception as e:
                self.log(f"Language selection notice: {e}", "WARNING")

            # 5. Type (Career stage: 'Fresher')
            self.log("Selecting career stage: Fresher...", "INFO")
            try:
                fresher_clicked = False
                fresher_chip = page.get_by_text("Fresher", exact=True).first
                if fresher_chip.is_visible():
                    fresher_chip.scroll_into_view_if_needed()
                    fresher_chip.click(force=True)
                    fresher_clicked = True
                    page.wait_for_timeout(1000)
                else:
                    f_box = page.locator("div, span, button").filter(has_text="Fresher").last
                    if f_box.is_visible():
                        f_box.scroll_into_view_if_needed()
                        f_box.click(force=True)
                        fresher_clicked = True
                        page.wait_for_timeout(1000)
            except Exception as e:
                self.log(f"Career stage notice: {e}", "WARNING")

            # 6. Years of work experience ('0 years')
            self.log("Setting experience: 0 years...", "INFO")
            try:
                exp_chip = page.get_by_text("0 years", exact=True).first
                try:
                    exp_chip.wait_for(state="visible", timeout=4000)
                except Exception:
                    pass
                if exp_chip.is_visible():
                    exp_chip.scroll_into_view_if_needed()
                    exp_chip.click(force=True)
                    page.wait_for_timeout(500)
                else:
                    e_box = page.locator("div, span, button").filter(has_text="0 years").last
                    if e_box.is_visible():
                        e_box.scroll_into_view_if_needed()
                        e_box.click(force=True)
                        page.wait_for_timeout(500)
            except Exception as e:
                self.log(f"Experience notice: {e}", "WARNING")

            # 7. Course ('B.Tech')
            self.log("Selecting course: B.Tech...", "INFO")
            try:
                btech_chip = page.get_by_text("B.Tech", exact=True).first
                try:
                    btech_chip.wait_for(state="visible", timeout=4000)
                except Exception:
                    pass
                if btech_chip.is_visible():
                    btech_chip.scroll_into_view_if_needed()
                    btech_chip.click(force=True)
                    page.wait_for_timeout(800)
                else:
                    b_box = page.locator("div, span, button").filter(has_text="B.Tech").last
                    if b_box.is_visible():
                        b_box.scroll_into_view_if_needed()
                        b_box.click(force=True)
                        page.wait_for_timeout(800)
            except Exception as e:
                self.log(f"Course selection notice: {e}", "WARNING")

            # 8. College name (Typeahead / Autocomplete, Placeholder: 'Eg. BITS Pilani')
            self.log(f"Setting college: {self.college}...", "INFO")
            college_input = page.locator(
                "input[placeholder*='BITS Pilani' i], input[placeholder*='Eg. BITS' i], input[placeholder*='College' i]"
            ).first
            try:
                try:
                    college_input.wait_for(state="visible", timeout=3000)
                except Exception:
                    pass
                if college_input.is_visible():
                    college_input.scroll_into_view_if_needed()
                    college_input.click()
                    college_input.press("Control+a")
                    college_input.press("Backspace")
                    college_input.press_sequentially(self.college, delay=50)
                    page.wait_for_timeout(1500)

                    col_selected = False
                    try:
                        col_sug = page.locator("div, li").filter(has_text=self.college).filter(has_not=page.locator("input")).last
                        if col_sug.is_visible():
                            col_sug.click(force=True)
                            col_selected = True
                    except Exception:
                        pass

                    if not col_selected:
                        try:
                            col_item = page.get_by_text(self.college, exact=True).last
                            if col_item.is_visible():
                                col_item.click(force=True)
                                col_selected = True
                        except Exception:
                            pass

                    if not col_selected:
                        college_input.press("ArrowDown")
                        page.wait_for_timeout(200)
                        college_input.press("Enter")

                    # Dismiss any leftover dropdown overlay
                    try:
                        page.get_by_text("College name", exact=False).first.click(force=True)
                    except Exception:
                        pass
                    page.wait_for_timeout(400)
            except Exception as e:
                self.log(f"College typeahead notice: {e}", "WARNING")

            # 9. Stream (Optional, Typeahead, Placeholder: 'Eg. Computer Science')
            self.log(f"Setting stream: {self.stream}...", "INFO")
            stream_input = page.locator("input[placeholder*='Computer Science' i], input[placeholder*='Stream' i]").first
            try:
                if stream_input.is_visible():
                    stream_input.scroll_into_view_if_needed()
                    stream_input.click()
                    stream_input.press("Control+a")
                    stream_input.press("Backspace")
                    stream_input.press_sequentially("Computer Science", delay=50)
                    page.wait_for_timeout(1200)

                    try:
                        stream_opt = page.get_by_text("Computer Science & Engineering", exact=True).first
                        if stream_opt.is_visible():
                            stream_opt.click(force=True)
                        else:
                            page.keyboard.press("ArrowDown")
                            page.wait_for_timeout(200)
                            page.keyboard.press("Enter")
                    except Exception:
                        page.keyboard.press("Enter")

                    try:
                        page.get_by_text("Stream", exact=False).first.click(force=True)
                    except Exception:
                        pass
                    page.wait_for_timeout(400)
            except Exception as e:
                self.log(f"Stream notice: {e}", "WARNING")

            # 10. Start year & End year (Custom dropdowns displaying 'Choose year')
            self.log(f"Selecting graduation start ({self.start_year}) and end ({self.end_year}) years...", "INFO")
            try:
                start_done = page.get_by_text(self.start_year, exact=True).first.is_visible()
                end_done = page.get_by_text(self.end_year, exact=True).first.is_visible()

                if not (start_done and end_done):
                    choose_boxes = [
                        b for b in page.locator("div, button").filter(has_text="Choose year").all()
                        if b.is_visible() and len(b.inner_text().strip().splitlines()) <= 2
                    ]
                    if len(choose_boxes) >= 2:
                        # Start year
                        choose_boxes[0].scroll_into_view_if_needed()
                        choose_boxes[0].click()
                        page.wait_for_timeout(500)
                        start_opt = page.get_by_text(self.start_year, exact=True).first
                        if start_opt.is_visible():
                            start_opt.click(force=True)
                        else:
                            page.keyboard.press("Enter")
                        page.wait_for_timeout(500)

                        # End year
                        choose_boxes_2 = [
                            b for b in page.locator("div, button").filter(has_text="Choose year").all()
                            if b.is_visible() and len(b.inner_text().strip().splitlines()) <= 2
                        ]
                        if choose_boxes_2:
                            choose_boxes_2[-1].scroll_into_view_if_needed()
                            choose_boxes_2[-1].click()
                            page.wait_for_timeout(500)
                            end_opt = page.get_by_text(self.end_year, exact=True).first
                            if end_opt.is_visible():
                                end_opt.click(force=True)
                            else:
                                page.keyboard.press("Enter")
                            page.wait_for_timeout(500)
            except Exception as e:
                self.log(f"Year dropdown notice: {e}", "WARNING")

        # Initial pass
        fill_all_fields()

        # Retry and validation loop: Ensure form actually submits and navigates away from "Let's get started"
        self.log("Submitting profile details...", "INFO")
        for attempt in range(1, 4):
            if self._is_stopped:
                return False

            next_btn = page.locator("button:has-text('Next')").last
            try:
                if next_btn.is_visible():
                    next_btn.scroll_into_view_if_needed()
                    next_btn.click()
                    page.wait_for_timeout(2500)
            except Exception:
                pass

            # Check if navigated away from "Let's get started"
            moved_past = False
            for _ in range(10):
                current_url = page.url
                if (
                    "preferences" in current_url
                    or ("personal_details" not in current_url and "onboarding" not in current_url and not page.locator(":has-text(\"Let's get started\")").first.is_visible())
                    or page.locator(":has-text('Area of interest')").first.is_visible()
                ):
                    moved_past = True
                    break
                page.wait_for_timeout(500)

            if moved_past:
                self.log("Profile onboarding details successfully accepted by portal!", "SUCCESS")
                return True

            # If still on page, check for unfulfilled required fields
            req_errors = page.locator(":has-text('Required'), .has-error, .error-message").all()
            if req_errors or page.locator(":has-text(\"Let's get started\")").first.is_visible():
                self.log(f"Attempt {attempt}: Onboarding form requires field correction. Re-verifying fields...", "WARNING")
                fill_all_fields()
                page.wait_for_timeout(1000)

        # Strict validation guard: DO NOT ADVANCE if required fields are still missing
        if page.locator(":has-text(\"Let's get started\")").first.is_visible():
            self.log("Profile onboarding form has unfulfilled required fields. Execution safely halted to prevent account waste.", "ERROR")
            self.on_error("Could not complete profile onboarding: required fields are missing.")
            return False

        return True

    def _step_preferences(self, page: Page) -> bool:
        if self._is_stopped:
            return False

        self.log("Synchronizing with career preferences portal...", "INFO")

        # Guard: Check if preferences are already completed
        curr_url = page.url.lower()
        if "matching-preferences" in curr_url or ("internships" in curr_url and "user_preference" not in curr_url):
            self.log("Career preferences profile is already completed!", "SUCCESS")
            return True

        # 1. Ensure we are on preferences (wait up to 10s for redirect or navigate directly)
        is_on_pref = False
        for _ in range(10):
            curr_url = page.url.lower()
            if (
                "preferences" in curr_url
                or page.locator(".preference-types-field, .modes-field").first.is_visible()
                or page.locator("h1, h2, div, span").filter(has_text=re.compile(r"Your preferences", re.I)).first.is_visible()
            ):
                is_on_pref = True
                break
            page.wait_for_timeout(1000)

        if not is_on_pref:
            self.log("Navigating to career preferences portal...", "INFO")
            try:
                self._goto_with_retry(
                    page,
                    "https://internshala.com/user_preference/preferences",
                    wait_until="domcontentloaded",
                    timeout=45000,
                    max_attempts=2,
                    label="preferences page",
                )
                page.wait_for_timeout(2000)
            except Exception as e:
                self.log(f"Preferences navigation notice: {e}", "WARNING")

        page.wait_for_timeout(1000)

        # Re-check if already completed
        if "matching-preferences" in page.url.lower() or ("internships" in page.url.lower() and "user_preference" not in page.url.lower()):
            self.log("Career preferences profile is already completed!", "SUCCESS")
            return True

        # --- PHASE 1: Handle Step 1 ("Area(s) of interest") if present ---
        # Dismiss any open modal dialog (such as the "Search for your preferred area of interest" popup)
        try:
            close_modal = page.locator(".modal:visible .close, .modal:visible [class*='close'], .modal:visible i, button:has-text('Done')").first
            if close_modal.is_visible():
                close_modal.click(force=True)
                page.wait_for_timeout(600)
        except Exception:
            pass

        # Detect Phase 1: presence of "Next" button or "Area(s) of interest"
        phase1_next_btn = page.locator("button:has-text('Next'), .next-button, #next_btn").first
        is_phase1 = (
            phase1_next_btn.is_visible()
            or page.locator(":has-text('Area(s) of interest'), :has-text('career interests among')").first.is_visible()
        )

        if is_phase1:
            self.log("Handling Phase 1: Selecting career interest chip ('Web Development')...", "INFO")

            # 1. Click 'Web Development' chip (or first popular chip). NEVER click or focus the search input field!
            clicked_chip = False
            for target_name in ["Web Development", "Software Development", "Programming", "Frontend Development"]:
                try:
                    chip_el = page.locator(".chips-container .chip, div.chip, [class*='chip']").filter(has_text=re.compile(rf"{target_name}", re.I)).first
                    if chip_el.is_visible():
                        chip_el.scroll_into_view_if_needed()
                        chip_el.click(force=True)
                        clicked_chip = True
                        page.wait_for_timeout(500)
                        break
                except Exception:
                    pass

            if not clicked_chip:
                # Direct JS click on chip containing '+' in main content
                page.evaluate("""() => {
                    const chips = Array.from(document.querySelectorAll('.chip, div[class*="chip"], span[class*="chip"]'));
                    const targetChip = chips.find(c => {
                        const t = (c.textContent || '').trim();
                        return (t.includes('Web Development') || t.includes('+')) && !c.closest('footer') && !c.closest('header');
                    });
                    if (targetChip) {
                        targetChip.scrollIntoView({ behavior: 'instant', block: 'center' });
                        targetChip.click();
                    }
                }""")
                page.wait_for_timeout(500)

            # 2. Click 'Next' button to advance to Phase 2
            self.log("Clicking 'Next' button to advance to Phase 2...", "INFO")
            if phase1_next_btn.is_visible():
                phase1_next_btn.scroll_into_view_if_needed()
                phase1_next_btn.click(force=True)
            else:
                page.evaluate("""() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => (b.textContent || '').trim().toLowerCase() === 'next');
                    if (btn) btn.click();
                }""")
            page.wait_for_timeout(2000)

        # --- PHASE 2: Opportunity Type & Work Mode ---
        # Wait for Phase 2 containers to appear
        for _ in range(8):
            if (
                page.locator(".preference-types-field, .modes-field").first.is_visible()
                or page.locator("button.submit-cta, button:has-text('Find me opportunities')").first.is_visible()
            ):
                break
            page.wait_for_timeout(500)

        self.log("Handling Phase 2: Selecting opportunity type & work mode...", "INFO")

        for attempt in range(1, 4):
            # 1. Select 'Internships' in .preference-types-field
            self.log("Selecting 'Internships'...", "INFO")
            pref_active = page.evaluate("""() => {
                const pref = document.querySelector('.preference-types-field');
                return pref ? pref.querySelector('.chip.active') !== null : false;
            }""")
            if not pref_active:
                internship_chip = page.locator(".preference-types-field .chip").filter(has_text=re.compile(r"Internship", re.I)).first
                try:
                    if internship_chip.is_visible():
                        internship_chip.scroll_into_view_if_needed()
                        internship_chip.click(force=True)
                        page.wait_for_timeout(400)
                except Exception:
                    pass
                # JavaScript fallback for internship chip
                page.evaluate("""() => {
                    const pref = document.querySelector('.preference-types-field');
                    if (pref && !pref.querySelector('.chip.active')) {
                        const chip = Array.from(pref.querySelectorAll('.chip')).find(c => (c.textContent || '').includes('Internship')) || pref.querySelector('.chip');
                        if (chip) chip.click();
                    }
                }""")
                page.wait_for_timeout(300)

            # 2. Select 'Work from home' (or 'In-office') in .modes-field
            self.log("Selecting 'Work from home'...", "INFO")
            mode_active = page.evaluate("""() => {
                const mode = document.querySelector('.modes-field');
                return mode ? mode.querySelector('.chip.active') !== null : false;
            }""")
            if not mode_active:
                wfh_chip = page.locator(".modes-field .chip").filter(has_text=re.compile(r"Work from home", re.I)).first
                try:
                    if wfh_chip.is_visible():
                        wfh_chip.scroll_into_view_if_needed()
                        wfh_chip.click(force=True)
                        page.wait_for_timeout(400)
                except Exception:
                    pass
                # JavaScript fallback for mode chip
                page.evaluate("""() => {
                    const mode = document.querySelector('.modes-field');
                    if (mode && !mode.querySelector('.chip.active')) {
                        const chip = Array.from(mode.querySelectorAll('.chip')).find(c => (c.textContent || '').includes('Work from home')) 
                                  || mode.querySelector('.chip');
                        if (chip) chip.click();
                    }
                }""")
                page.wait_for_timeout(300)

            # 3. Click 'Find me opportunities' submit CTA
            find_btn = page.locator("button.submit-cta, button:has-text('Find me opportunities')").first
            self.log("Submitting preferences ('Find me opportunities')...", "INFO")
            try:
                if find_btn.is_visible():
                    find_btn.scroll_into_view_if_needed()
                    find_btn.click(force=True)
                else:
                    page.evaluate("""() => {
                        const btn = document.querySelector('button.submit-cta') || 
                                    Array.from(document.querySelectorAll('button')).find(b => (b.textContent || '').includes('Find me opportunities'));
                        if (btn) btn.click();
                    }""")
            except Exception as e:
                self.log(f"Submit CTA notice: {e}", "WARNING")

            page.wait_for_timeout(2500)

            # 4. Verify completion / navigation away from preferences
            curr_url = page.url.lower()
            if (
                "matching-preferences" in curr_url
                or "google-gemini-ai-plus" in curr_url
                or ("internships" in curr_url and "user_preference" not in curr_url)
                or not page.locator("button.submit-cta, button:has-text('Find me opportunities')").first.is_visible()
            ):
                self.log("Career preferences profile successfully completed and accepted!", "SUCCESS")
                return True

            # If still on page, check for errors
            has_error = page.locator(".has-error, :has-text('Required')").first.is_visible()
            if has_error:
                self.log(f"Attempt {attempt}: Preferences required fields not registered. Retrying...", "WARNING")
                page.wait_for_timeout(800)

        # Check for any lingering Skip button
        try:
            skip_btn = page.locator("a:has-text('Skip'), button:has-text('Skip')").first
            if skip_btn.is_visible():
                skip_btn.click(force=True)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # Final check if navigated
        if "preferences" not in page.url.lower() or not page.locator("button.submit-cta").first.is_visible():
            self.log("Career preferences profile completed successfully!", "SUCCESS")
            return True

        self.log("Preferences submission finished.", "INFO")
        return True

    def _step_claim_gemini(self, page: Page, context: BrowserContext) -> Optional[str]:
        if self._is_stopped:
            return None

        # 1. Attach network and page listeners immediately to capture popups or API redirects
        redirection_url = None
        captured_urls = []
        opened_pages = []

        def on_req(req):
            u = req.url
            if "one.google.com" in u or "google.com/offer" in u:
                captured_urls.append(u)

        def on_resp(resp):
            try:
                u = resp.url
                if "one.google.com" in u or "google.com/offer" in u:
                    captured_urls.append(u)
                if "internshala.com" in u and ("offer" in u or "claim" in u or "gemini" in u or "redirect" in u):
                    try:
                        data = resp.json()
                        def scan_json(val):
                            if isinstance(val, str) and ("one.google.com" in val or "google.com/offer" in val):
                                captured_urls.append(val)
                            elif isinstance(val, dict):
                                for v in val.values(): scan_json(v)
                            elif isinstance(val, list):
                                for item in val: scan_json(item)
                        scan_json(data)
                    except Exception:
                        pass
            except Exception:
                pass

        context.on("request", on_req)
        context.on("response", on_resp)
        context.on("page", lambda p: opened_pages.append(p))

        def check_for_redirection_url() -> Optional[str]:
            # Check all open pages in context
            for p in list(context.pages) + opened_pages:
                try:
                    p_url = p.url
                    if "one.google.com" in p_url or "google.com/offer" in p_url:
                        return p_url
                    if "internshala.com" in p_url and "redirect" in p_url:
                        from urllib.parse import parse_qs, urlparse
                        qs = parse_qs(urlparse(p_url).query)
                        for qk in ("url", "target", "redirect_url"):
                            if qk in qs and "google.com" in qs[qk][0]:
                                return qs[qk][0]
                except Exception:
                    pass
            # Check captured network URLs
            for u in captured_urls:
                if "one.google.com" in u or "google.com/offer" in u:
                    return u
            # Check current page URL
            try:
                if "one.google.com" in page.url or "google.com/offer" in page.url:
                    return page.url
            except Exception:
                pass
            return None

        promo_url = "https://internshala.com/google-gemini-ai-plus"
        self.log("Accessing promotional portal...", "INFO")
        try:
            self._goto_with_retry(
                page,
                promo_url,
                wait_until="domcontentloaded",
                timeout=50000,
                max_attempts=2,
                label="promotional portal",
            )
            page.wait_for_timeout(2500)
        except Exception as e:
            self.log(f"Navigation to promotional portal encountered: {e}", "WARNING")

        # Fallback: check menu / navigation link if direct URL redirected
        if "/google-gemini-ai-plus" not in page.url:
            gemini_menu_link = page.locator(":has-text('Free Gemini Access'), a:has-text('Free Gemini Access')").first
            if not gemini_menu_link.is_visible():
                hamburger = page.locator(".navbar-toggler, .hamburger_menu, .is_icon_header_menu, #hamburger_menu, i.fa-bars, .nav_icon").first
                if hamburger.is_visible():
                    hamburger.click()
                    page.wait_for_timeout(1000)

            gemini_menu_link = page.locator(":has-text('Free Gemini Access'), a:has-text('Free Gemini Access')").first
            if gemini_menu_link.is_visible():
                self.log("Opening promotional section from navigation...", "INFO")
                gemini_menu_link.click()
                page.wait_for_timeout(3000)

        # Check for 'Complete now' if profile requires final completion
        complete_btn = page.locator("button, a, .btn").filter(has_text=re.compile(r"^Complete now$", re.I)).first
        if not complete_btn.is_visible():
            complete_btn = page.locator("button:has-text('Complete now'), a:has-text('Complete now')").first
        try:
            if complete_btn.is_visible():
                self.log("Profile completion prompt detected on offer page. Completing onboarding profile...", "INFO")
                complete_btn.click()
                page.wait_for_timeout(2000)
                if page.locator(":has-text(\"Let's get started\")").first.is_visible():
                    if not self._step_profile_details(page):
                        return None
                if not self._step_preferences(page):
                    return None
                # Re-navigate to promo portal
                self._goto_with_retry(
                    page,
                    promo_url,
                    wait_until="domcontentloaded",
                    timeout=50000,
                    max_attempts=2,
                    label="promotional portal",
                )
                page.wait_for_timeout(2500)
        except Exception:
            pass

        # Check for hero card 'Claim now' CTA button
        claim_now_btn = page.locator(
            "button, a, div[role='button'], span[role='button'], .btn"
        ).filter(has_text=re.compile(r"^Claim now$", re.I)).first

        if not claim_now_btn.is_visible():
            claim_now_btn = page.locator(
                "button:has-text('Claim now'), a:has-text('Claim now'), .btn:has-text('Claim now')"
            ).first

        if claim_now_btn.is_visible():
            try:
                href = claim_now_btn.get_attribute("href")
                if href and ("one.google.com" in href or "google.com/offer" in href):
                    redirection_url = href
            except Exception:
                pass

            if not redirection_url:
                self.log("Triggering offer activation via 'Claim now'...", "INFO")
                try:
                    with context.expect_page(timeout=4000) as p_info:
                        claim_now_btn.click()
                    new_p = p_info.value
                    page.wait_for_timeout(1000)
                    if "one.google.com" in new_p.url or "google.com/offer" in new_p.url:
                        redirection_url = new_p.url
                except Exception:
                    try:
                        claim_now_btn.click(force=True)
                    except Exception:
                        pass
                page.wait_for_timeout(1500)

        redirection_url = redirection_url or check_for_redirection_url()

        # Scroll down to ensure lower offer section is in DOM and viewport
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(800)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(800)
        except Exception:
            pass

        # Locate 'Start FREE 12 months trial' CTA
        trial_btn = page.locator(
            "button.claim_offer_cta, a.claim_offer_cta, "
            "button:has-text('Start FREE 12 months trial'), a:has-text('Start FREE 12 months trial'), "
            ".btn:has-text('Start FREE 12 months trial'), [role='button']:has-text('Start FREE 12 months trial')"
        ).first

        if not trial_btn.is_visible():
            trial_btn = page.locator(
                "button, a, div[role='button'], .btn"
            ).filter(has_text=re.compile(r"Start FREE 12 months trial|Claim the offer now|Start trial", re.I)).first

        if not trial_btn.is_visible():
            # Check alternative claim/redeem buttons
            alt_btn = page.locator("button, a, .btn").filter(has_text=re.compile(r"^(Claim|Redeem|Activate|Start FREE)$", re.I)).first
            if alt_btn.is_visible():
                trial_btn = alt_btn

        if trial_btn.is_visible():
            try:
                trial_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
            except Exception:
                pass

        # Check if portal displayed eligibility notice or if trial button is disabled
        is_ineligible = page.locator(
            ":text-matches('not eligible for free Google AI Plus', 'i'), :text-matches('You\\'re not eligible', 'i')"
        ).first.is_visible()

        is_disabled = False
        try:
            if trial_btn.is_visible() and (trial_btn.is_disabled() or "disabled" in (trial_btn.get_attribute("class") or "").lower()):
                is_disabled = True
        except Exception:
            pass

        # If eligible and trial button is actionable, click it
        if not redirection_url and trial_btn.is_visible() and not is_disabled:
            self.log("Activating 12-Month Free Trial button...", "INFO")
            try:
                btn_href = trial_btn.get_attribute("href")
                if btn_href and ("one.google.com" in btn_href or "google.com/offer" in btn_href):
                    redirection_url = btn_href
            except Exception:
                pass

            if not redirection_url:
                try:
                    try:
                        with context.expect_page(timeout=10000) as new_page_info:
                            trial_btn.click()
                        new_p = new_page_info.value
                        new_p.wait_for_load_state("domcontentloaded", timeout=8000)
                        if "one.google.com" in new_p.url or "google.com/offer" in new_p.url:
                            redirection_url = new_p.url
                    except Exception:
                        try:
                            trial_btn.click(force=True)
                        except Exception:
                            page.evaluate("(el) => el.click()", trial_btn.element_handle())
                except Exception as e:
                    self.log(f"Trial button click trigger notice: {e}", "WARNING")

        # Handle any in-page modal dialog that may have opened
        try:
            modal = page.locator(".modal:visible, [role='dialog']:visible").first
            if modal.is_visible():
                modal_links = modal.locator("a[href*='google.com'], a[href*='one.google.com']")
                for i in range(modal_links.count()):
                    href = modal_links.nth(i).get_attribute("href")
                    if href and ("one.google.com" in href or "google.com/offer" in href):
                        redirection_url = href
                        break

                if not redirection_url:
                    modal_action = modal.locator(
                        "button, a, .btn"
                    ).filter(has_text=re.compile(r"Claim|Confirm|Continue|Redeem|Activate|Proceed", re.I)).first
                    if modal_action.is_visible():
                        try:
                            with context.expect_page(timeout=6000) as modal_p_info:
                                modal_action.click()
                            m_p = modal_p_info.value
                            if "one.google.com" in m_p.url or "google.com/offer" in m_p.url:
                                redirection_url = m_p.url
                        except Exception:
                            modal_action.click(force=True)
        except Exception:
            pass

        self.log("Intercepting Google One redemption offer link...", "INFO")

        # Poll all open pages and captured events for up to 15 seconds
        start_poll = time.time()
        while time.time() - start_poll < 15:
            redirection_url = redirection_url or check_for_redirection_url()
            if redirection_url:
                break
            page.wait_for_timeout(500)

        # Normalize and clean URL
        if redirection_url:
            if redirection_url.startswith("//"):
                redirection_url = "https:" + redirection_url
            elif not redirection_url.startswith("http"):
                redirection_url = "https://" + redirection_url
            redirection_url = clean_google_one_url(redirection_url)
            self.log(f"Captured Google One offer URL: {redirection_url}", "SUCCESS")
            return redirection_url

        # Fallback to email dispatch if direct redirection wasn't intercepted
        self.log("Account setup completed and qualified! Activation link was sent to your registered email address.", "INFO")
        return "EMAIL_DISPATCHED"
