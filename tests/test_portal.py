"""
Automated unit & smoke test suite for Gemini AI Plus Portal (v1.0.0).
Validates context-aware error normalization, dynamic UA generation, outdated
browser fallback, gateway retry behavior, headless->headed challenge fallback,
preferred browser selection, GitHub Releases update checker, and GUI smoke checks.
"""

import os
import sys
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from app.core.claimer import (
    GeminiAIClaimer,
    MIN_SUPPORTED_CHROMIUM_MAJOR,
    _HeadlessChallengeFallback,
    build_desktop_user_agent,
    clean_google_one_url,
    normalize_error_message,
    parse_browser_major_version,
)


def test_normalize_error_message_modes():
    reg_log = normalize_error_message("connection timed out", for_log=True, mode="register")
    assert "Registration" in reg_log and "Login" not in reg_log, reg_log
    reg_modal = normalize_error_message("connection timed out", for_log=False, mode="register")
    assert "registration gateway timed out" in reg_modal.lower(), reg_modal
    assert "mobile hotspot" in reg_modal.lower(), reg_modal

    inferred_reg = normalize_error_message(
        "Registration gateway failed to respond in time (connection timed out).",
        for_log=False,
    )
    assert "registration gateway timed out" in inferred_reg.lower(), inferred_reg
    assert "login" not in inferred_reg.lower(), inferred_reg

    login_modal = normalize_error_message("timed out", for_log=False, mode="login")
    assert "login operation timed out" in login_modal.lower(), login_modal
    inferred_login = normalize_error_message("Login portal timed out", for_log=True)
    assert inferred_login == "Login timed out.", inferred_login

    generic_log = normalize_error_message("request timeout", for_log=True)
    assert "Gateway connection timed out" in generic_log, generic_log

    reg_form = normalize_error_message("form not ready", for_log=True, mode="register")
    assert "Registration form" in reg_form, reg_form
    login_form = normalize_error_message("form not ready", for_log=True, mode="login")
    assert "Login form" in login_form, login_form

    assert "already registered" in normalize_error_message("Email already registered", for_log=True).lower()
    assert "403" in normalize_error_message("403 Forbidden", for_log=True)
    assert "429" in normalize_error_message("429 Too Many Requests", for_log=True)
    print("[OK] test_normalize_error_message_modes")


def test_dynamic_user_agent_and_version_parsing():
    assert parse_browser_major_version("135.0.7049.42") == 135
    assert parse_browser_major_version("chrome/118.0.5993.89") == 118
    assert parse_browser_major_version(None) is None
    assert parse_browser_major_version("unknown") is None

    ua_exact = build_desktop_user_agent("135.0.7049.42")
    assert "Chrome/135.0.7049.42 Safari/537.36" in ua_exact, ua_exact
    assert "HeadlessChrome" not in ua_exact

    ua_fallback = build_desktop_user_agent(None)
    assert "Chrome/" in ua_fallback and "HeadlessChrome" not in ua_fallback
    print("[OK] test_dynamic_user_agent_and_version_parsing")


def test_goto_with_retry():
    logs = []
    claimer = GeminiAIClaimer(
        email="test@gmail.com",
        password="Password123!",
        on_log=lambda msg, lvl="INFO": logs.append((lvl, msg)),
    )

    page = MagicMock()
    resp_ok = MagicMock(status=200)
    page.goto.side_effect = [PlaywrightTimeoutError("Timeout 50000ms"), resp_ok]

    with patch("app.core.claimer.time.sleep", return_value=None):
        resp = claimer._goto_with_retry(page, "https://example.com", timeout=50000, max_attempts=2, label="registration gateway")
    assert resp is resp_ok
    assert page.goto.call_count == 2
    assert any("Retrying" in m for _, m in logs), logs

    page2 = MagicMock()
    page2.goto.side_effect = PlaywrightTimeoutError("Timeout 50000ms")
    raised = False
    with patch("app.core.claimer.time.sleep", return_value=None):
        try:
            claimer._goto_with_retry(page2, "https://example.com", timeout=50000, max_attempts=2)
        except PlaywrightTimeoutError:
            raised = True
    assert raised and page2.goto.call_count == 2

    claimer._is_stopped = True
    page3 = MagicMock()
    res = claimer._goto_with_retry(page3, "https://example.com")
    assert res is None and page3.goto.call_count == 0
    print("[OK] test_goto_with_retry")


def test_outdated_chrome_falls_back_to_edge():
    logs = []
    claimer = GeminiAIClaimer(
        email="test@gmail.com",
        password="Password123!",
        headless=True,
        on_log=lambda msg, lvl="INFO": logs.append((lvl, msg)),
    )
    old_chrome = MagicMock()
    old_chrome.version = f"{MIN_SUPPORTED_CHROMIUM_MAJOR - 10}.0.0.0"
    new_edge = MagicMock()
    new_edge.version = "134.0.3124.72"

    p = MagicMock()
    p.chromium.launch.side_effect = [old_chrome, new_edge]

    chosen = claimer._launch_browser(p)
    assert chosen is new_edge
    assert old_chrome.close.called
    assert any("outdated Google Chrome" in m for _, m in logs), logs
    print("[OK] test_outdated_chrome_falls_back_to_edge")


def test_headless_challenge_fallback_signal():
    claimer = GeminiAIClaimer(
        email="test@gmail.com",
        password="Password123!",
        headless=True,
        allow_manual_verification=True,
    )
    claimer._headed_fallback_used = False

    page = MagicMock()
    page.goto.return_value = MagicMock(status=200)

    with patch.object(claimer, "_detect_verification_challenge", return_value="Cloudflare Turnstile"):
        triggered = False
        try:
            claimer._step_registration(page)
        except _HeadlessChallengeFallback:
            triggered = True
        assert triggered, "Expected _HeadlessChallengeFallback in headless mode"

    claimer._headed_fallback_used = True
    errors = []
    claimer.on_error = lambda e: errors.append(e)
    with patch.object(claimer, "_detect_verification_challenge", return_value="Cloudflare Turnstile"):
        ok = claimer._step_registration(page)
    assert ok is False and len(errors) == 1
    print("[OK] test_headless_challenge_fallback_signal")


def test_clean_google_one_url_regression():
    wrapped = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fone.google.com%2Foffer%2FABC123XYZ%3Futm%3D1&dsh=S-123"
    assert clean_google_one_url(wrapped) == "https://one.google.com/offer/ABC123XYZ"
    print("[OK] test_clean_google_one_url_regression")


def test_preferred_browser_selection():
    logs = []
    claimer = GeminiAIClaimer(
        email="test@gmail.com",
        password="Password123!",
        headless=True,
        preferred_browser="edge",
        on_log=lambda msg, lvl="INFO": logs.append((lvl, msg)),
    )
    edge_browser = MagicMock()
    edge_browser.version = "134.0.0.0"
    p = MagicMock()
    p.chromium.launch.return_value = edge_browser
    chosen = claimer._launch_browser(p)
    assert chosen is edge_browser
    p.chromium.launch.assert_called_once_with(channel="msedge", headless=True)
    assert any("(selected)" in m for _, m in logs), logs

    logs2 = []
    claimer2 = GeminiAIClaimer(
        email="test@gmail.com",
        password="Password123!",
        headless=True,
        preferred_browser="brave",
        on_log=lambda msg, lvl="INFO": logs2.append((lvl, msg)),
    )
    chrome_browser = MagicMock()
    chrome_browser.version = "134.0.0.0"
    p2 = MagicMock()
    p2.chromium.launch.return_value = chrome_browser
    with patch("os.path.exists", return_value=False):
        chosen2 = claimer2._launch_browser(p2)
    assert chosen2 is chrome_browser
    assert any("Falling back to automatic browser discovery" in m for _, m in logs2), logs2
    print("[OK] test_preferred_browser_selection")


def test_updater_semver_and_check():
    from app.core.updater import check_for_update, is_newer_version, parse_semver

    assert parse_semver("v1.0.0") == (1, 0, 0)
    assert parse_semver("v1.2.3") == (1, 2, 3)
    assert is_newer_version("v1.0.1", "v1.0.0") is True
    assert is_newer_version("v1.0.0", "v1.0.0") is False
    assert is_newer_version("v0.9.9", "v1.0.0") is False

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.read.return_value = b'{"tag_name": "v1.1.0", "html_url": "https://github.com/nmrisrl11/gemini-ai-plus-portal/releases/tag/v1.1.0", "draft": false, "prerelease": false}'
    fake_resp.__enter__.return_value = fake_resp
    with patch("urllib.request.urlopen", return_value=fake_resp):
        info = check_for_update(current_version="v1.0.0")
    assert info is not None and info["latest_version"] == "v1.1.0", info

    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        assert check_for_update(current_version="v1.0.0") is None
    print("[OK] test_updater_semver_and_check")


def test_gui_smoke():
    if os.environ.get("CI") and sys.platform != "win32":
        print("[SKIP] test_gui_smoke (non-Windows CI)")
        return
    from app.ui.main_window import GeminiClaimerApp

    app = GeminiClaimerApp()
    app.withdraw()
    try:
        assert hasattr(app, "opt_browser")
        assert app.opt_browser.get() == "Auto-Detect"
        assert set(app._browser_option_map.keys()) == {"Auto-Detect", "Google Chrome", "Microsoft Edge", "Brave"}
        app._set_fields_state("disabled")
        assert app.opt_browser.cget("state") == "disabled"
        app._set_fields_state("normal")
        assert app.opt_browser.cget("state") == "normal"

        app._show_update_banner("v1.0.1", "https://github.com/nmrisrl11/gemini-ai-plus-portal/releases/latest")
        assert "v1.0.1" in app.lbl_update_msg.cget("text")
        app.update_banner.pack_forget()
    finally:
        app.destroy()
    print("[OK] test_gui_smoke")


if __name__ == "__main__":
    test_normalize_error_message_modes()
    test_dynamic_user_agent_and_version_parsing()
    test_goto_with_retry()
    test_outdated_chrome_falls_back_to_edge()
    test_headless_challenge_fallback_signal()
    test_clean_google_one_url_regression()
    test_preferred_browser_selection()
    test_updater_semver_and_check()
    test_gui_smoke()
    print("\nALL PORTAL TESTS PASSED!")
