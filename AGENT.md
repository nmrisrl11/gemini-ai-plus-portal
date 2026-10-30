# AGENT CONTEXT & HANDOFF — GOOGLE AI PLUS PORTAL

> **Document Type:** Developer & Agent Handoff / Architecture Blueprint  
> **Application:** Google AI Plus — 1-Year Access Portal  
> **Current Version:** `v1.0.0` (Private Desktop Edition)  
> **Repository:** `https://github.com/nmrisrl11/gemini-ai-plus-claimer.git`  
> **Primary Developer:** `@nmrisrl11`  
> **Last Updated:** October 2026  

---

## 1. Executive Summary

**Google AI Plus Portal** is a high-performance Windows desktop automation tool designed to streamline the student promotional onboarding and link acquisition process for **12 months of free Google AI Plus (Gemini Advanced and 2TB Google One cloud storage)**.

The software replaces tedious manual navigation, regional demographic formatting, and multi-step verification forms with a 1-click automated background routine. It prompts the user only when their 6-digit email OTP arrives, extracts the official single-use redemption link (`https://one.google.com/offer/...`), and backs up the credentials locally.

---

## 2. Tech Stack & Key Dependencies

- **Language:** Python 3.10 – 3.12 (64-bit)
- **GUI Framework:** `customtkinter` (Dark Mode, blue theme)
- **Automation Engine:** `playwright.sync_api` (Zero-bloat system channel attachment: `chrome` $\to$ fallback `msedge`)
- **Image Processing:** `pillow` (PIL) for QR rendering, icon manipulation, ray-cast alpha matting, and ICO generation
- **Packaging:** `pyinstaller` (Produces single-file, zero-dependency `dist\Google AI Plus Portal v1.0.0.exe`)
- **OS Platform:** Windows 10 & Windows 11 (requires Win32 Shell API for `AppUserModelID` taskbar binding)

---

## 3. Architecture & File Layout

```text
gemini-ai-plus-claimer/
├── constants.py                     # Version, dynamic environment detection & path resolution
├── claimer.py                       # Core Playwright engine, demographic generators & error normalizers
├── gui.py                           # CustomTkinter GUI, queues, DPI mipmaps & event loops
├── main.py                          # Dual GUI/CLI entry point with AppUserModelID registration
├── convert_icon.py                  # High-DPI ICO & transparent PNG generator with ray-casting
├── build_portable.bat               # 1-click standalone portable builder (double-clickable)
├── build_portable.py                # Scripted portable builder
├── run.bat                          # 1-click Windows development launcher
├── requirements.txt                 # Pinned dependencies
├── README.md                        # Project documentation & user guides
├── AGENT.md                         # This file: Agent context, decisions, and handoff
├── .gitignore                       # Protects results/, .venv/, dist/, build/, and caches
├── images/                          # Merged asset directory
│   ├── app_icon.ico                 # Multi-layer sharpened Windows icon (16x16 to 256x256)
│   ├── app_icon.png                 # 512x512 transparent PNG
│   ├── qrcode-bmc.png               # Buy Me a Coffee donation QR
│   ├── qrcode-gcash.JPG             # GCash donation QR
│   ├── shuffle.png                  # Randomize Info button icon
│   └── logo_raw.jpg                 # Source reference image from Gemini
├── dialogs/                         # Modular dialog controllers
│   ├── __init__.py                  # Package exports
│   ├── about_modal.py               # About, expectations & privacy dialog (F1)
│   ├── diagnostics_modal.py         # Developer edge case testing suite (F12)
│   ├── otp_dialog.py                # 6-digit keystroke-validated OTP input dialog
│   └── support_modal.py             # Voluntary donation modal (BMC & GCash)
├── account_recovery/                # CDP live browser recovery safety net
│   ├── README.md                    # Recovery instructions
│   ├── resume_browser_session.py    # CDP session attach script
│   └── run_account_recovery.bat     # 1-click recovery launcher
├── results/                         # Output archive for generated credentials & links (.gitignored)
└── dist/                            # Production output
    └── Google AI Plus Portal v1.0.0.exe  # Standalone portable application (61.4 MB)
```

---

## 4. Critical Workflows & Business Logic

### A. Onboarding & Registration Pipeline (`claimer.py`)
1. **Demographic Generation:** Uses randomized, valid Indian student demographics (`FIRST_NAMES`, `LAST_NAMES`, Indian phone prefixes `+91 6-9...`).
2. **Gateway Navigation:** Navigates to the partner onboarding portal (`/student/personal_details` and `/student/onboarding`).
3. **Form Synchronization:** Locator-based waits for fields (`#first_name`, `#last_name`, `#email`, `#password`, `#phone`).
4. **OTP Interception:**
   - Thread communicates with GUI thread via `queue.Queue`.
   - GUI displays modal `OTPDialog` with strict keystroke filtering (digits only, max 6).
   - If invalid code is entered, the server returns an error, triggering the recovery loop to re-prompt without crashing.
5. **Career Preferences & Auto-Completion:** Automatically selects student preferences, graduation years, and fresher qualifications.
6. **Offer Link Acquisition:** Locates the Google One promotional card, extracts `https://one.google.com/offer/...`, and logs completion.

### B. Controlled Error Normalization (`normalize_error_message`)
Upstream servers return raw JSON or unformatted English errors. `normalize_error_message()` cleanses them:
- **Already Registered:** Explains that each promotional link requires a fresh account registration and prompts for a new email.
- **Invalid OTP:** Re-prompts the user with clear instructions.
- **Security Challenge (CAPTCHA / Turnstile):** Triggers `WAITING_USER` status, stops automated submissions safely, and alerts the user instead of getting IP-blocked.

### C. Live Activity Feed & Guide Transition
- Upon launch, the activity feed displays a clean 4-step **Quick Guide**.
- Once the user starts provisioning, the feed clears the guide and streams real-time bracketed logs: `[i]`, `[OK]`, `[!]`, `[X]`, `[...]`.
- If reset, the feed restores the initial Quick Guide.

---

## 5. Key Architecture & Design Decisions

### 1. Dynamic Execution Mode (`SHOW_VISUAL_BROWSER_OPTION`)
- **Requirement:** The visual browser checkbox must be `True` by default during local Python development (for debugging), but **automatically `False`** when compiled as a portable `.exe`.
- **Implementation in [`constants.py`](constants.py):**
  ```python
  IS_PORTABLE = getattr(sys, "frozen", False)
  SHOW_VISUAL_BROWSER_OPTION = not IS_PORTABLE
  ```
  - In source mode: Checkbox is visible and pre-checked.
  - In portable `.exe`: Checkbox is completely hidden, forcing silent background headless execution.

### 2. PyInstaller Asset & Results Path Handling
- In frozen single-file executables, bundled files are extracted to temporary directory `sys._MEIPASS`.
- **Handling in [`constants.py`](constants.py):**
  - `PROJECT_ROOT = getattr(sys, "_MEIPASS", ...)` allows QR images and icons to load seamlessly.
  - `RESULTS_DIR = os.path.join(os.path.dirname(sys.executable), "results")` ensures result text files are saved **beside the user's `.exe`**, NOT inside the temporary extraction folder!

### 3. Windows Taskbar AppUserModelID & High-DPI Mipmaps
- **Problem:** Python apps on Windows default to the generic Python logo on the taskbar and group under `python.exe`.
- **Fix in [`main.py`](main.py) and [`gui.py`](gui.py):**
  ```python
  if sys.platform == "win32":
      ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("nmrisrl11.googleaiplus.claimerportal.v100")
  ```
- **Taskbar Sharpness:**
  - `self.iconphoto(True, *self._taskbar_icons)` feeds 256, 64, 48, 32, 24, 16px high-DPI RGBA bitmaps directly to Windows DWM.
  - Small icon layers (16–48px) are sharpened with adaptive UnsharpMasking in `convert_icon.py` to prevent blur on 125%/150% scaled displays.

### 4. Zero-Bloat Playwright Channel Attachment
- Uses `channel="chrome"` with fallback to `channel="msedge"`.
- Bypasses the need to download or bundle the 400MB Chromium binary with the portable `.exe`.

### 5. UI Cleanliness & Copywriting Rules
- **No Emojis:** All UI buttons, headers, activity logs, and modal labels use clean ASCII or text badges (`[i]`, `[OK]`, `[!]`, `[X]`).
- **No "Open Source" Claims:** All user-facing copy references "Desktop Edition" or "Private Desktop Utility".
- **Action Bar Simplicity:** Top-right action row contains only `[ Support Dev ]`. The About modal is accessible via the footer link and the <kbd>F1</kbd> hotkey.

---

## 6. Testing & Quality Assurance

A comprehensive unit test suite is maintained in `scratch/test_suite.py` containing **30 automated tests**:
- Normalization & error handling tests.
- CAPTCHA / Cloudflare Turnstile passive vs active challenge tests.
- UI state transitions, stepper resets, button label validations.
- Modal instantiations (`AboutModal`, `SupportModal`, `DiagnosticsModal`, `OTPDialog`).
- Build mode simulation (verifying `IS_PORTABLE` toggles).

**How to run tests:**
```powershell
& ".\.venv\Scripts\python.exe" "C:\Users\NOMER ISRAEL\.gemini\antigravity\brain\40fad3d3-ae4e-4e51-aeda-7286d50bea21\scratch\test_suite.py"
```

### D. Career Preferences Synchronization & Claim Extraction (Updated October 2026)
1. **Preferences Onboarding (`_step_preferences`):**
   - Eliminates input clicking to avoid triggering the "Search for your preferred area of interest" modal.
   - Clicks interest chips directly (`Web Development +`), then clicks `Next` to advance to Phase 2.
   - In Phase 2, clicks `Internships +` and `Work from home +` chips, then submits via `Find me opportunities`.
   - Verified with automatic retries and multi-attempt validation.
2. **Offer Link Capture & Dual-Stage Claim (`_step_claim_gemini`):**
   - Intercepts outgoing network requests (`context.on("request")`), responses, and JSON API payloads for `one.google.com` or `google.com/offer` right from Step 0.
   - Directly clicks hero card `Claim now` button using exact text match to trigger section scroll and unlock the offer.
   - Scrolls down to `Claim the offer now` and clicks the primary CTA (`Start FREE 12 months trial`).
   - Watches newly opened tabs/popups (`context.on("page")`) and polls all context pages for up to 15 seconds.
   - If direct on-screen claim is ineligible or dispatched to email, gracefully returns `"EMAIL_DISPATCHED"` with brand-neutral next steps.
3. **Canonical URL Extractor (`clean_google_one_url`):**
   - Automatically unescapes and cleans redirect wrappers (e.g. `accounts.google.com/v3/signin/...continue=...`) to yield permanent, clean `https://one.google.com/offer/<CODE>` URLs.
   - Eliminates session tokens (`dsh=S-...`) to prevent multi-device expiration or login loops.
4. **Multi-Browser Recovery Safety Net (`account_recovery/resume_browser_session.py`):**
   - Attaches directly over CDP (port 9222) to any supported browser (Brave, Chrome, Edge).
   - Brand-neutral UI and automatic saving of credentials / redemption URLs to `results/`.
5. **Headless Execution in Portable Build:**
   - Standalone executable automatically defaults to silent background execution (`SHOW_VISUAL_BROWSER_OPTION = not IS_PORTABLE`), keeping the UX clean and desktop-native.

---

## 7. Packaging & Portable Builds

To build a fresh portable standalone `.exe`:
1. Simply double-click [`build_portable.bat`](build_portable.bat) (or run `python build_portable.py`).
2. The script cleans previous artifacts and runs PyInstaller with:
   - `--noconsole`
   - `--onefile`
   - `--name "Google AI Plus Portal {APP_VERSION}"`
   - `--icon="images/app_icon.ico"`
   - `--add-data="images;images"`
   - `--collect-all="customtkinter"`
   - `--collect-all="playwright"`
3. Output executable: `dist\Google AI Plus Portal v1.0.0.exe` (61.4 MB).

---

## 8. Rules for Future Agents

1. **Maintain Git Hygiene:** Never commit `results/`, `dist/`, or `.venv/`. Check [`.gitignore`](.gitignore) before adding files.
2. **Preserve Encoding:** Always open and save files with `encoding="utf-8"`.
3. **Preserve UI Tone:** Do not add emojis or casual slang to buttons, logs, or dialogs. Maintain clean, professional copywriting.
4. **Preserve Version Centralization:** Version is defined once in `constants.py` as `APP_VERSION`. All scripts and modals import from there.
5. **Keep Automated Tests Passing:** After making changes to `claimer.py`, `gui.py`, or `constants.py`, run the test suite to ensure all 30 tests pass.
