# Multi-Browser Account Recovery Safety Net

This utility serves as a **safety net** for accounts that have already passed email OTP verification but were interrupted before completing the multi-step profile onboarding (`/student/personal_details` or `/student/onboarding`).

## Supported Browsers
- **Google Chrome**
- **Brave Browser**
- **Microsoft Edge**

## Why This Exists
When an existing account attempts to log in again through the public login modal (`/login/user`), the security gateway often flags automated submissions with a server verification requirement.

By attaching directly to an **already-authenticated session** inside your chosen browser via Chrome DevTools Protocol (CDP), this tool:
1. Bypasses the login form and verification hurdles completely.
2. Automatically navigates to the profile onboarding page.
3. Auto-fills and selects all required onboarding fields (Location, Gender, English, Fresher, Experience, Course, College, Stream, Years).
4. Submits the form and completes career preferences.
5. Claims the 12-Month Google AI Plus free trial offer link and extracts the canonical `https://one.google.com/offer/<CODE>` URL (or outputs clear email dispatch guidance if delivered via email).
6. Automatically archives credentials and links to the `results/` directory.

## How to Use
1. Make sure you are logged in to your account in **Brave Browser**, **Google Chrome**, or **Microsoft Edge**.
2. Run [`run_account_recovery.bat`](run_account_recovery.bat) (or run `python resume_browser_session.py`).
3. Select your browser `[1] Brave`, `[2] Chrome`, or `[3] Edge`.
4. The tool will cleanly attach to your browser context, restore your active tabs, complete onboarding live on your screen, and display your offer link.
