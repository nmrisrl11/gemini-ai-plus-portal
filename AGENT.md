# AGENT CONTEXT & HANDOFF — GEMINI AI PLUS PORTAL

> **Document Type:** Developer & Agent Handoff / Architecture Blueprint  
> **Application:** Gemini AI Plus Portal  
> **Current Version:** `v1.0.1` (Open Source Desktop Edition — MIT License)  
> **Repository:** `https://github.com/nmrisrl11/gemini-ai-plus-portal.git`  
> **Primary Developer:** `@nmrisrl11`  
> **Last Updated:** November 2026  

---

## 1. Executive Summary

**Gemini AI Plus Portal** is a high-performance Windows desktop automation tool designed to streamline the student promotional onboarding and link acquisition process for **12 months of Google AI Plus at no cost (400 GB cloud storage across Google Photos, Drive, and Gmail, double Gemini app usage limits with Hydrogen model access, Google Flow, Google Search Nano Banana, Gemini in Gmail, Gemini Notebook, and Google Flow Music)**.

The software replaces tedious manual navigation, regional demographic formatting, and multi-step verification forms with a 1-click automated background routine. It prompts the user only when their 6-digit email OTP arrives, extracts the official single-use redemption link (`https://one.google.com/offer/...`), and backs up the credentials locally.

---

## 2. Tech Stack & Key Dependencies

- **Language:** Python 3.10 – 3.12 (64-bit)
- **GUI Framework:** `customtkinter` (Dark Mode, blue theme)
- **Automation Engine:** `playwright.sync_api` (Intelligent multi-browser cascade: Chrome $\to$ Edge $\to$ Brave/Chromium direct scan $\to$ Playwright cache)
- **Image Processing:** `pillow` (PIL) for QR rendering, icon manipulation, ray-cast alpha matting, and ICO generation
- **Packaging (Primary):** `nuitka` v4.3+ (Translates Python directly to native C, compiled via MinGW-w64 GCC into tamper-proof x86-64 machine code, compressed with `zstandard`; produces single-file `dist\Gemini AI Plus Portal v1.0.1.exe` @ ~43.0 MB)
- **Packaging (Fallback):** `pyinstaller` (Alternative standard Python bytecode packager)
- **OS Platform:** Windows 10 & Windows 11 (requires Win32 Shell API for `AppUserModelID` taskbar binding)

---

## 3. Architecture & File Layout

```text
gemini-ai-plus-portal/
├── .github/
│   └── workflows/
│       └── release.yml                  # Automated Windows Nuitka build + VirusTotal release CI
├── main.py                              # Dual GUI/CLI entry point with AppUserModelID registration
├── run.bat                              # 1-click Windows development launcher
├── requirements.txt                     # Pinned dependencies (including nuitka & zstandard)
├── LICENSE                              # MIT License
├── README.md                            # Project documentation & user guides
├── AGENT.md                             # This file: Agent context, decisions, and handoff
├── .gitignore                           # Protects results/, .venv/, dist/, build/, and caches
├── app/                                 # Core application package
│   ├── __init__.py                      # Package exports
│   ├── config.py                        # Version, dynamic environment detection & path resolution
│   ├── core/                            # Business logic & automation engine
│   │   ├── __init__.py
│   │   ├── claimer.py                   # Core Playwright engine, demographic generators & error normalizers
│   │   └── updater.py                   # Cloudflare R2 latest.json updater & remote status.json pause checker
│   └── ui/                              # CustomTkinter desktop interface layer
│       ├── __init__.py
│       ├── theme.py                     # Centralized design tokens, typography & Win11 titlebar helpers
│       ├── main_window.py               # CustomTkinter GUI, queues, DPI mipmaps & event loops
│       └── dialogs/                     # Modular dialog controllers
│           ├── __init__.py              # Package exports
│           ├── about_modal.py           # About, expectations & privacy dialog (F1)
│           ├── diagnostics_modal.py     # Developer edge case testing suite (F12)
│           ├── otp_dialog.py            # 6-digit keystroke-validated OTP input dialog
│           └── support_modal.py         # Voluntary donation modal (BMC & GCash)
├── assets/                              # Static visual assets
│   └── images/                          # Merged image asset directory
│       ├── app_icon.ico                 # Multi-layer sharpened Windows icon (16x16 to 256x256)
│       ├── app_icon.png                 # 512x512 transparent PNG
│       ├── check.png                    # Stepper completion white checkmark icon
│       ├── logo_raw.jpg                 # Source reference image from Gemini (excluded from builds)
│       ├── preview.PNG                  # Desktop UI preview screenshot (excluded from builds)
│       ├── qrcode-bmc.png               # Buy Me a Coffee donation QR
│       ├── qrcode-gcash.JPG             # GCash donation QR
│       └── shuffle.png                  # Randomize button icon
├── scripts/                             # Packaging & asset build tooling
│   ├── build_nuitka.bat                 # 1-click hardened native C builder (Nuitka + Zstandard)
│   ├── build_nuitka.py                  # Scripted native C compiler (tamper-proof machine code)
│   ├── build_portable.bat               # 1-click fallback portable builder (PyInstaller)
│   ├── build_portable.py                # Scripted PyInstaller builder
│   ├── convert_icon.py                  # High-DPI ICO & transparent PNG generator with ray-casting
│   ├── upload_r2.py                     # Cloudflare R2 release & latest.json uploader (boto3/OpenSSL)
│   └── virustotal_scan.py               # VirusTotal API v3 release scanner & Markdown report generator
├── tools/                               # Standalone companion utilities
│   └── account_recovery/                # CDP live browser recovery safety net
│       ├── README.md                    # Recovery instructions
│       ├── resume_browser_session.py    # CDP session attach script
│       └── run_account_recovery.bat     # 1-click recovery launcher
├── tests/                               # Automated unit & GUI smoke test suite
│   └── test_portal.py
├── results/                             # Output archive for generated credentials & links (.gitignored)
└── dist/                                # Production output
    └── Gemini AI Plus Portal v1.0.1.exe # Hardened native standalone binary (~43.0 MB)
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

### 1. Dynamic Execution Mode & Dual Environment Detection (`IS_PORTABLE`)
- **Requirement:** The visual browser checkbox must be `True` by default during local Python development (for debugging), but **automatically `False`** when compiled as a standalone `.exe`.
- **Implementation in [`app/config.py`](app/config.py):**
  ```python
  IS_PORTABLE = getattr(sys, "frozen", False) or "__compiled__" in globals()
  SHOW_VISUAL_BROWSER_OPTION = not IS_PORTABLE
  ```
  - In source mode: Checkbox is visible and pre-checked.
  - In portable `.exe` (PyInstaller or Nuitka): Checkbox is completely hidden, forcing silent background headless execution.

### 2. Dual Nuitka & PyInstaller Asset & Results Path Handling
- **PyInstaller Mode (`sys.frozen` & `sys._MEIPASS`):**
  - `PROJECT_ROOT = sys._MEIPASS`
  - `EXE_DIR = os.path.dirname(sys.executable)`
  - `RESULTS_DIR = os.path.join(EXE_DIR, "results")`
- **Nuitka Onefile Mode (`__compiled__`):**
  - `PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (extracted runtime bundle folder)
  - `EXE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))` (physical directory holding the `.exe`)
  - `RESULTS_DIR = os.path.join(EXE_DIR, "results")`
- **Result:** Result text files and credentials are saved **beside the user's `.exe`**, never inside temporary extraction paths.

### 3. Native C Compilation & Anti-Reverse Engineering (Nuitka)
- **Problem:** PyInstaller executables can be unpacked in seconds using `pyinstxtractor` and decompiled back to raw Python source with `uncompyle6` or `pylingual`.
- **Solution:** `scripts/build_nuitka.py` translates all Python modules into genuine C code, compiles them with MinGW GCC into native x86-64 machine instructions (binary PE), and compresses the onefile payload using `zstandard`.
- **Security:** No `.pyc` bytecode exists in the binary. Decompilers and unpackers are completely thwarted.
- **Fast Rebuilds:** Uses `ccache` to cache compiled C objects, reducing iterative build times from ~15m to <2m.
- **OneDrive Lock Bypass:** Compiles intermediate objects inside `%LOCALAPPDATA%\NuitkaBuild\` to eliminate OneDrive file-sync lock contention.

### 4. Windows Taskbar AppUserModelID & High-DPI Mipmaps
- **Problem:** Python apps on Windows default to the generic Python logo on the taskbar and group under `python.exe`.
- **Fix in [`main.py`](main.py) and [`app/ui/main_window.py`](app/ui/main_window.py):**
  ```python
  if sys.platform == "win32":
      ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("nmrisrl11.geminiaiplus.portal.v100")
  ```
- **Taskbar Sharpness:**
  - `self.iconphoto(True, *self._taskbar_icons)` feeds 256, 64, 48, 32, 24, 16px high-DPI RGBA bitmaps directly to Windows DWM.
  - Small icon layers (16–48px) are sharpened with adaptive UnsharpMasking in `scripts/convert_icon.py` to prevent blur on 125%/150% scaled displays.

### 5. Intelligent Multi-Browser Discovery Cascade
- Uses `_launch_browser(self, p)` in `app/core/claimer.py` with 5 tiers:
  1. `channel="chrome"`
  2. `channel="msedge"` (Built-in on 100% of Windows 10/11 machines)
  3. Direct executable scan for Brave, Chrome, Edge, Opera, and Vivaldi in Program Files, Program Files (x86), and %LOCALAPPDATA%
  4. Local Playwright cache in `%LOCALAPPDATA%\ms-playwright`
  5. Fallback `p.chromium.launch()` for unbundled source development
- Bypasses the need to download or bundle the 400MB Chromium binary with the portable `.exe`.

### 6. UI Cleanliness & Copywriting Rules
- **No Emojis:** All UI buttons, headers, activity logs, and modal labels use clean ASCII or text badges (`[i]`, `[OK]`, `[!]`, `[X]`).
- **Open Source License:** Released under the MIT License (`LICENSE`). Keep user-facing copy clean and professional.
- **Action Bar Simplicity:** Top-right action row contains only `[ Support Dev ]`. The About modal is accessible via the footer link and the <kbd>F1</kbd> hotkey.

---

## 6. Testing & Quality Assurance

An automated unit and GUI smoke test suite is maintained in `tests/test_portal.py`:
- Context-aware error normalization (`register` vs `login`) and HTTP 403/429 handling.
- Dynamic User-Agent generation and outdated Chrome (`< v120`) Edge fallback.
- Gateway navigation retry (`_goto_with_retry`) and headless-to-headed verification challenge fallback.
- Preferred browser selection and GitHub Releases update checker (`app/core/updater.py`).
- Live CustomTkinter GUI smoke test (browser dropdown + update banner).

**How to run tests:**
```powershell
& ".\.venv\Scripts\python.exe" "tests\test_portal.py"
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
4. **Multi-Browser Recovery Safety Net (`tools/account_recovery/resume_browser_session.py`):**
   - Attaches directly over CDP (port 9222) to any supported browser (Brave, Chrome, Edge).
   - Brand-neutral UI and automatic saving of credentials / redemption URLs to `results/`.
5. **Headless Execution in Portable Build:**
   - Standalone executable automatically defaults to silent background execution (`SHOW_VISUAL_BROWSER_OPTION = not IS_PORTABLE`), keeping the UX clean and desktop-native.

---

## 7. Packaging & Portable Builds

The project provides dual build pipelines to serve both tamper-proof production deployment and development fallback:

### Primary: Hardened Native C Compiler (Nuitka + GitHub Actions CI)
1. Double-click [`scripts/build_nuitka.bat`](scripts/build_nuitka.bat) or run `python scripts/build_nuitka.py` (default `--mode onefile` single `.exe`; pass `--mode standalone` for a folder + ZIP).
2. Translates Python directly into C, compiles with MinGW-w64 GCC (`--jobs=4`, `--lto=no`), compresses with `zstandard`, isolates intermediate compilation inside a space-free workspace (`C:\NuitkaBuild\gemini-portal`), and bundles only the 6 runtime image assets (excluding `logo_raw.jpg` and `preview.PNG`).
3. Output executable: `dist\Gemini AI Plus Portal v1.0.1.exe` (~43 MB).
4. **CI, Code Signing & VirusTotal:** `.github/workflows/release.yml` builds on `windows-latest` for `v*` tags or manual dispatch, optionally code-signs via SignPath.io (`SIGNPATH_API_TOKEN` + `SIGNPATH_ORGANIZATION_ID`), generates `SHA256SUMS.txt`, runs `scripts/virustotal_scan.py` via `${{ secrets.VIRUSTOTAL_API_KEY }}`, and embeds the full VirusTotal report into the GitHub Release notes.
5. **Security:** Native machine code; zero `.pyc` files; immune to `pyinstxtractor`.

### Fallback: Standard Portable Packager (PyInstaller)
1. Double-click [`scripts/build_portable.bat`](scripts/build_portable.bat) (or run `python scripts/build_portable.py`).
2. Packages bytecode into a standard PyInstaller archive with:
   - `--noconsole`
   - `--onefile`
   - `--name "Gemini AI Plus Portal {APP_VERSION}"`
   - `--icon="assets/images/app_icon.ico"`
   - `--add-data="assets/images;assets/images"`
   - `--collect-all="customtkinter"`
   - `--collect-all="playwright"`
3. Output executable: `dist\Gemini AI Plus Portal v1.0.1.exe` (~61.4 MB).

---

## 8. Rules for Future Agents

1. **Maintain Git Hygiene:** Never commit `results/`, `dist/`, or `.venv/`. Check [`.gitignore`](.gitignore) before adding files.
2. **Preserve Encoding:** Always open and save files with `encoding="utf-8"`.
3. **Preserve UI Tone:** Do not add emojis or casual slang to buttons, logs, or dialogs. Maintain clean, professional copywriting.
4. **Preserve Version Centralization:** Version is defined once in `app/config.py` as `APP_VERSION`. All scripts and modals import from there.
5. **Keep Automated Tests Passing:** After making changes to `app/core/claimer.py`, `app/ui/main_window.py`, or `app/config.py`, run UI and module verification checks to ensure all workflows pass.
