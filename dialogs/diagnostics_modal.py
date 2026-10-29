"""
Edge Case Diagnostics & Simulation modal for development and testing.
Accessible via F12 or Ctrl+Shift+D.
"""

import os
from tkinter import messagebox
import customtkinter as ctk

from claimer import normalize_error_message
from constants import IMAGES_DIR
from dialogs.otp_dialog import OTPDialog


class DiagnosticsModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Edge Case Diagnostics & Simulation")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ico_path = os.path.join(IMAGES_DIR, "app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.after(200, lambda: self.iconbitmap(ico_path))
            except Exception:
                pass

        # Center relative to parent window
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f"+{max(0, parent_x + 180)}+{max(0, parent_y + 120)}")

        ctk.CTkLabel(
            self,
            text="Edge Case Testing Suite",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8",
        ).pack(pady=(18, 5))

        ctk.CTkLabel(
            self,
            text="Test every edge case instantly without burning an email:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        ).pack(pady=(0, 15))

        # Test 1: Invalid OTP Modal & Re-prompt
        ctk.CTkButton(
            self,
            text="1. Test Invalid OTP Modal & Recovery Loop",
            height=36,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._test_invalid_otp,
        ).pack(fill="x", padx=30, pady=6)

        # Test 2: Server Rejection Catching
        ctk.CTkButton(
            self,
            text="2. Test Already-Registered Rejection Alert",
            height=36,
            fg_color="#d97706",
            hover_color="#b45309",
            command=self._test_server_rejection,
        ).pack(fill="x", padx=30, pady=6)

        # Test 3: Redemption Result Card & Copy Action
        ctk.CTkButton(
            self,
            text="3. Test Redemption Link Banner & Copywriting",
            height=36,
            fg_color="#16a34a",
            hover_color="#15803d",
            command=self._test_success_flow,
        ).pack(fill="x", padx=30, pady=6)

        # Test 4: CAPTCHA / Security Challenge Edge Case
        ctk.CTkButton(
            self,
            text="4. Test CAPTCHA / Security Challenge Notice",
            height=36,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self._test_captcha_challenge,
        ).pack(fill="x", padx=30, pady=6)

        ctk.CTkButton(
            self,
            text="Close Diagnostics",
            height=32,
            fg_color="#334155",
            hover_color="#475569",
            command=self.destroy,
        ).pack(pady=(16, 10))

    def _test_invalid_otp(self):
        self.destroy()
        self.parent._append_log("[Diagnostic] Simulating invalid OTP entry & re-prompt...", "INFO")
        email = self.parent.entry_email.get().strip() or "testuser@gmail.com"
        dlg = OTPDialog(self.parent, email, error_message="Invalid OTP entered! Please check your email and try again.")
        self.parent.wait_window(dlg)
        if dlg.otp_value:
            self.parent._append_log(f"[Diagnostic] User re-entered OTP: {dlg.otp_value}", "SUCCESS")
            messagebox.showinfo("Diagnostic Success", f"Invalid OTP edge case verified! Code received: {dlg.otp_value}", parent=self.parent)

    def _test_server_rejection(self):
        self.destroy()
        self.parent._append_log("[Diagnostic] Simulating server rejection alert catch...", "INFO")
        raw_msg = "This email id is already registered. Please use forgot password if you do not remember your password or click here to login."
        log_clean = normalize_error_message(raw_msg, for_log=True)
        self.parent._append_log(f"Notice: {log_clean}", "ERROR")
        self.parent._on_error_callback(raw_msg)
        self.parent._append_log("Error interception & controlled copywriting verified.", "SUCCESS")

    def _test_success_flow(self):
        self.destroy()
        self.parent._append_log("[Diagnostic] Simulating successful offer link extraction...", "INFO")
        sample_link = "https://one.google.com/offer/D46KVH0ZESYPYY1MCM1G"
        self.parent._on_success_callback(sample_link)
        self.parent._append_log("[Diagnostic] Success banner active. Profile fields locked. Click 'Provision Another Account' to reset and start a new session.", "SUCCESS")

    def _test_captcha_challenge(self):
        self.destroy()
        self.parent._append_log("[Diagnostic] Simulating security verification challenge detection...", "INFO")
        challenge_msg = "Verification challenge detected (Google reCAPTCHA Challenge); manual action required."
        self.parent._append_log(challenge_msg, "WAITING_USER")
        self.parent._set_status("Awaiting Manual Verification...", "#f59e0b")
        norm_err = normalize_error_message("captcha verification challenge detected", for_log=False)
        messagebox.showinfo(
            "Manual Verification Required",
            f"Diagnostic: Security challenge detected.\n\n{norm_err}",
            parent=self.parent,
        )
        self.parent._append_log("Security challenge detection handled safely without repeated submissions.", "SUCCESS")
        self.parent._set_status("System Ready", "#10b981")
