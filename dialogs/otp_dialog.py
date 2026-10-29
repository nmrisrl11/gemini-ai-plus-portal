"""
Email verification OTP input dialog with strict 6-digit keystroke validation.
"""

import os
import customtkinter as ctk

from constants import IMAGES_DIR


class OTPDialog(ctk.CTkToplevel):
    def __init__(self, parent, email: str, error_message: str = None):
        super().__init__(parent)
        self.title("Email Verification — 6 Digit Code")
        height = 360 if error_message else 330
        self.geometry(f"460x{height}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ico_path = os.path.join(IMAGES_DIR, "app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.after(200, lambda: self.iconbitmap(ico_path))
            except Exception:
                pass

        self.otp_value = None

        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f"+{parent_x + 80}+{parent_y + 100}")

        self.lbl_title = ctk.CTkLabel(
            self,
            text="Verify Your Email",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8",
        )
        self.lbl_title.pack(pady=(20, 4))

        self.lbl_desc = ctk.CTkLabel(
            self,
            text=f"A 6-digit verification code was sent to:\n{email}",
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8",
        )
        self.lbl_desc.pack(pady=(0, 8))

        if error_message:
            self.lbl_err = ctk.CTkLabel(
                self,
                text=f"Notice: {error_message}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f87171",
                wraplength=410,
            )
            self.lbl_err.pack(pady=(0, 8))

        # OTP Entry with strict keystroke filtering (digits only, max 6 chars)
        vcmd = (self.register(self._validate_otp_input), "%P")
        self.entry_otp = ctk.CTkEntry(
            self,
            placeholder_text="• • • • • •",
            width=230,
            height=46,
            justify="center",
            font=ctk.CTkFont(size=24, weight="bold"),
            validate="key",
            validatecommand=vcmd,
        )
        self.entry_otp.pack(pady=(6, 4))
        self.entry_otp.focus()

        # Dynamic counter and helper status label
        self.lbl_counter = ctk.CTkLabel(
            self,
            text="0 / 6 digits entered",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.lbl_counter.pack(pady=(0, 10))

        # Submit button - starts disabled until exactly 6 digits are entered
        self.btn_submit = ctk.CTkButton(
            self,
            text="Verify Code & Proceed",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            fg_color="#334155",
            hover_color="#0369a1",
            text_color="#94a3b8",
            command=self._on_submit,
        )
        self.btn_submit.pack(pady=(4, 15))

        # Event bindings
        self.entry_otp.bind("<Return>", lambda e: self._on_submit())
        self.entry_otp.bind("<Control-v>", self._handle_paste)
        self.entry_otp.bind("<Control-V>", self._handle_paste)
        self.entry_otp.bind("<<Paste>>", self._handle_paste)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _validate_otp_input(self, proposed: str) -> bool:
        """Restricts input strictly to numeric digits only and maximum 6 characters."""
        if len(proposed) > 6:
            return False
        if proposed != "" and not proposed.isdigit():
            return False
        self._update_counter_and_button(proposed)
        return True

    def _update_counter_and_button(self, val: str):
        length = len(val)
        if length == 0:
            self.lbl_counter.configure(text="0 / 6 digits entered", text_color="#64748b")
            self.btn_submit.configure(state="disabled", fg_color="#334155", text_color="#94a3b8")
        elif length < 6:
            self.lbl_counter.configure(text=f"{length} / 6 digits entered", text_color="#f59e0b")
            self.btn_submit.configure(state="disabled", fg_color="#334155", text_color="#94a3b8")
        else:  # exactly 6 digits
            self.lbl_counter.configure(text="6 of 6 digits entered - ready to verify", text_color="#10b981")
            self.btn_submit.configure(state="normal", fg_color="#0284c7", text_color="#ffffff")

    def _handle_paste(self, event=None):
        """Filters pasted text to only extract digits and limit to 6 digits."""
        try:
            raw = self.clipboard_get()
        except Exception:
            return "break"

        digits = "".join(ch for ch in raw if ch.isdigit())[:6]
        if digits:
            self.entry_otp.delete(0, "end")
            self.entry_otp.insert(0, digits)
            self._update_counter_and_button(digits)
        return "break"

    def _on_close(self):
        self.otp_value = None
        self.destroy()

    def _on_submit(self):
        val = self.entry_otp.get().strip()
        if len(val) != 6 or not val.isdigit():
            self.lbl_counter.configure(text="Exactly 6 digits required to verify", text_color="#f87171")
            return
        self.otp_value = val
        self.destroy()
