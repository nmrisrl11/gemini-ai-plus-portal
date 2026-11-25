"""
Edge Case Diagnostics & Simulation modal for development and testing.
Accessible via F12 or Ctrl+Shift+D.
"""

from tkinter import messagebox
import customtkinter as ctk

from app.core.claimer import normalize_error_message
from app.config import IMAGES_DIR
from app.ui.dialogs.otp_dialog import OTPDialog
from app.ui import theme as T


class DiagnosticsModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Edge Case Diagnostics & Simulation")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_WINDOW)
        self.transient(parent)
        self.grab_set()

        T.center_modal(self, parent, 540, 510)
        T.apply_modal_icon(self, IMAGES_DIR)
        self.after(60, lambda: T.apply_win11_titlebar(self, T.BG_WINDOW, T.TEXT_PRIMARY))

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=22, pady=20)

        # Header
        head_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        head_row.pack(fill="x")

        ctk.CTkLabel(
            head_row,
            text="Diagnostics & Simulation",
            font=T.ui_font(17, "bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        dev_pill = ctk.CTkFrame(
            head_row,
            fg_color=T.BG_BADGE,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=5,
        )
        dev_pill.pack(side="right", pady=2)
        ctk.CTkLabel(
            dev_pill,
            text="DEV SUITE",
            font=T.mono_font(10, "bold"),
            text_color=T.TEXT_MUTED,
        ).pack(padx=7, pady=1)

        ctk.CTkLabel(
            wrapper,
            text="Simulate edge cases and UI state transitions without consuming an email.",
            font=T.ui_font(12),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", pady=(4, 16))

        # Structured Simulation Rows
        self._add_sim_row(
            wrapper,
            tag="OTP",
            tag_bg=T.ACCENT_SOFT,
            tag_fg=T.ACCENT_TEXT,
            title="Invalid OTP Modal & Recovery Loop",
            desc="Opens OTP prompt with an error alert banner and validates re-entry.",
            command=self._test_invalid_otp,
        )
        self._add_sim_row(
            wrapper,
            tag="ERR",
            tag_bg=T.DANGER_BG,
            tag_fg=T.DANGER_TEXT,
            title="Already-Registered Rejection Alert",
            desc="Verifies server rejection normalization and user-facing notice.",
            command=self._test_server_rejection,
        )
        self._add_sim_row(
            wrapper,
            tag="OK",
            tag_bg=T.SUCCESS_BG,
            tag_fg=T.SUCCESS_TEXT,
            title="Redemption Link Banner & Success State",
            desc="Activates the full result card, locks fields, and updates stepper.",
            command=self._test_success_flow,
        )
        self._add_sim_row(
            wrapper,
            tag="WAIT",
            tag_bg=T.WARNING_BG,
            tag_fg=T.WARNING_TEXT,
            title="CAPTCHA / Security Challenge Notice",
            desc="Triggers WAITING_USER status without repeated form submissions.",
            command=self._test_captcha_challenge,
        )

        # Footer
        footer = ctk.CTkFrame(wrapper, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=(10, 0))

        ctk.CTkButton(
            footer,
            text="Close",
            width=100,
            height=34,
            font=T.ui_font(12, "bold"),
            fg_color=T.BTN_SECONDARY,
            hover_color=T.BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_PRIMARY,
            corner_radius=7,
            command=self.destroy,
        ).pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())

    def _add_sim_row(self, parent, tag: str, tag_bg: str, tag_fg: str, title: str, desc: str, command):
        card = ctk.CTkFrame(
            parent,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=9,
        )
        card.pack(fill="x", pady=(0, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        inner.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkLabel(
            inner,
            text=tag,
            width=46,
            height=24,
            font=T.mono_font(10, "bold"),
            fg_color=tag_bg,
            text_color=tag_fg,
            corner_radius=5,
        )
        badge.grid(row=0, column=0, padx=(0, 12), sticky="w")

        text_col = ctk.CTkFrame(inner, fg_color="transparent")
        text_col.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            text_col,
            text=title,
            font=T.ui_font(12, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            text_col,
            text=desc,
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=330,
        ).pack(fill="x")

        ctk.CTkButton(
            inner,
            text="Run",
            width=66,
            height=28,
            font=T.ui_font(11, "bold"),
            fg_color=T.BTN_SECONDARY,
            hover_color=T.BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_PRIMARY,
            corner_radius=6,
            command=command,
        ).grid(row=0, column=2, padx=(12, 0), sticky="e")

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
        self.parent._set_status("Awaiting Manual Verification...", T.WARNING)
        norm_err = normalize_error_message("captcha verification challenge detected", for_log=False)
        messagebox.showinfo(
            "Manual Verification Required",
            f"Diagnostic: Security challenge detected.\n\n{norm_err}",
            parent=self.parent,
        )
        self.parent._append_log("Security challenge detection handled safely without repeated submissions.", "SUCCESS")
        self.parent._set_status("System Ready", T.SUCCESS)
